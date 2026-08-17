import base64
import os, json
import uuid
import requests
from requests.auth import HTTPBasicAuth

from django.conf import settings
from django.utils import timezone

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from OpenSSL import crypto

from exceptions import UserAdviceException
from payins.processors.mpesa import MpesaC2BProcessor

CERT_PATH = settings.BASE_DIR / "ProductionCertificate.cer"


class MpesaB2CProcessor(MpesaC2BProcessor):

    def __init__(self):
        self.consumerKey = settings.B2C_CONSUMER_KEY
        self.consumerSecret = settings.B2C_CONSUMER_SECRET
        self.shortcode = settings.B2C_SHORTCODE
        self.initiator_name = settings.B2C_INITIATOR_NAME
        self.initiator_password = settings.B2C_INITIATOR_PASSWORD
        self.callback_url = f"{settings.APP_URL}/api/v1/callback/mpesa/b2c/"

    def pass_encryptor(self):
        initiator_password = self.initiator_password
        initiator_password = bytes(initiator_password, "utf_8")

        f = open(CERT_PATH, "rb")
        cert = f.read()
        cert_file = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
        pubKeyObject = cert_file.get_pubkey()
        pubKeyString = crypto.dump_publickey(crypto.FILETYPE_PEM, pubKeyObject)
        pubKey = RSA.import_key(pubKeyString)
        signer = PKCS1_v1_5.new(pubKey)
        security_cred = signer.encrypt(initiator_password)
        encoded_credential = base64.b64encode(security_cred)
        encoded_credential = str(encoded_credential, "utf-8")

        return encoded_credential

    def b2c_send(self, payload):

        token = self.get_mpesa_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        encoded_credential = self.pass_encryptor()
        print(f"Encoded Credential: {encoded_credential}")  # Debugging log

        amount = payload.get("amount")
        receiver = payload.get("phone_number")
        remarks = payload.get("remarks", "Instant Payout")
        reference = payload.get("reference")

        payload = {
            "OriginatorConversationID": reference,
            "InitiatorName": self.initiator_name,
            "SecurityCredential": encoded_credential,
            # "CommandID": "PromotionPayment",
            "CommandID": "SalaryPayment",
            "Amount": str(amount),
            "PartyA": self.shortcode,
            "PartyB": receiver,
            "Remarks": remarks,
            "QueueTimeOutURL": self.callback_url,
            "ResultURL": self.callback_url,
            "Occassion": "Kizuka Payout",
        }
        payload_copy = payload.copy()
        payload_copy.pop("SecurityCredential")
        print(f"Payload for B2C: {payload_copy}")  # Avoid logging sensitive info

        response = requests.post(
            f"{settings.MPESA_BASE_API_URL}/mpesa/b2c/v1/paymentrequest",
            headers=headers,
            json=payload,
        )
        print(response.text)
        json_resp = response.json()
        return response.status_code, json_resp

    def move_funds(self, amount):
        encoded_credential = self.pass_encryptor()
        payload = {
            "Initiator": self.initiator_name,
            # "SecurityCredential": encoded_credential,
            "SecurityCredential": "BuWYmOhta/ynsvddWQ+98K97O5eBSSFdeuBipRR9QPHtd63lfcLHGwJ7tKf6FiTqYSUqkXAqN+Nz/DdcClJZVGZDFZk9Y1yPsZKHK8DKD7Lxon4LmMCN0nBdSxwp/LqmX8UV490/PQV+PIRzOjrWAgL7if7Fam9c9UaJfM73qkBEBeyaHB79497WtX49QHCydrJBmSnF+rZBK+FVk8KKpOfzVsPxFDJhtpQ6ruJk7ffCHKX15dHihKYB1A/8ahLYZ6zQ83dPrfr8NS78pLqcJJoY58mhoRVN6Nj/m6yLH2Xn33vXC13l5P26Tt4emBc9wJY4ZaDNcdxXn8C1inMqAg==",
            "CommandID": "BusinessPayToBulk",
            "SenderIdentifierType": "4",
            "RecieverIdentifierType": "4",
            "Amount": str(amount),
            "PartyA": self.shortcode,
            "PartyB": self.shortcode,
            "AccountReference": f"float_buy{timezone.now().strftime('%Y%m%d%H%M%S')}",
            "Remarks": "OK",
            "QueueTimeOutURL": self.callback_url,
            "ResultURL": self.callback_url
        }
        token = self.get_mpesa_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        response = requests.post(
            f"{settings.MPESA_BASE_API_URL}/mpesa/b2b/v1/paymentrequest",
            headers=headers,
            json=payload,
        )
        print(response.text)
        json_resp = response.json()
        return response.status_code, json_resp

    def validate_account(self, account, account_type=None, bank_code=None):
        if account_type not in ["PayBill", "TillNumber"]:
            raise UserAdviceException(
                "account_type acceptable values are 'PayBill' or 'TillNumber' "
            )

        account_identifier = "2"
        if account_type == "PayBill":
            account_identifier = "4"

        url = f"{settings.MPESA_BASE_API_URL}/sfcverify/v1/query/info"
        token = self.get_mpesa_token()
        headers = {
            "Authorization": f"Bearer {token}",
            # "SourceSystem": "Apigee",
            # "SourceIdentityToken": "token",
            # "CorrelationConversationID": "1712908333",
            # "RouteID": "query-org-info",
        }

        payload = {"IdentifierType": account_identifier, "Identifier": account}

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Account validation response: {resp.status_code} - {resp.text}")
        if resp.status_code != 200:
            raise UserAdviceException("invalid request or account number")

        resp = resp.json()
        if (
            resp.get("ResponseCode") != "4000"
            or resp.get("ResponseMessage") != "Success"
        ):
            raise UserAdviceException(resp.get("DetailedMessage"))

        return {
            "account": resp.get("OrganizationShortCode"),
            "name": resp.get("OrganizationName"),
            "status": resp.get("ResponseMessage"),
        }

    def query_transaction_status(self, payout):
        """
        Ask Safaricom for the status of a payout stuck in PROCESSING.

        Per Daraja docs, the original transaction can be identified by either its
        M-Pesa receipt (TransactionID) or the OriginatorConversationID it was sent
        with - we always have the latter (payout.init_response is set once in
        send() and never overwritten), so we use it even when no receipt was ever
        recorded. This query is itself async: this call only returns an accept/
        reject ack, the actual TransactionStatus arrives later at ResultURL.
        """
        token = self.get_mpesa_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        encoded_credential = self.pass_encryptor()

        original_conversation_id = (payout.init_response or {}).get("OriginatorConversationID")

        payload = {
            "Initiator": self.initiator_name,
            "SecurityCredential": encoded_credential,
            "CommandID": "TransactionStatusQuery",
            "TransactionID": payout.provider_reference or "",
            "OriginatorConversationID": original_conversation_id,
            "PartyA": self.shortcode,
            "IdentifierType": "4",
            "ResultURL": self.callback_url,
            "QueueTimeOutURL": self.callback_url,
            "Remarks": f"Status check for PO_{payout.alias_id}",
            "Occasion": "Status Check",
        }

        resp = requests.post(
            f"{settings.MPESA_BASE_API_URL}/mpesa/transactionstatus/v1/query",
            headers=headers,
            json=payload,
        )
        json_resp = resp.json()
        return resp.status_code, json_resp


class MpesaHakikisha():

    def __init__(self):
        self.hakikisha_consumer_key = settings.HAKIKISHA_CONSUMER_KEY
        self.hakikisha_consumer_secret = settings.HAKIKISHA_SECRET
        self.api_url = settings.HAKIKISHA_BASE_URL
        self.shortcode = settings.B2C_SHORTCODE

    def get_token(self):
        url = f"{self.api_url}/oauth2/v1/generate?grant_type=client_credentials"
        resp = requests.post(
            url,
            auth=HTTPBasicAuth(
                self.hakikisha_consumer_key, self.hakikisha_consumer_secret
            ),
            timeout=60,
        )
        if not resp.status_code == 200:
            raise Exception(resp.text)

        access_token = resp.json().get("access_token")
        expires_in = resp.json().get("expires_in")
        return access_token

    def validate_account(self, payload):
        token = self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        receiver = payload.get("phone_number")

        payload = {
            "header": {
                "requestID": str(uuid.uuid4()),
                "timestamp": timezone.now().timestamp(),
            },
            "body": {
                "msisdn": receiver,
                "shortcode": self.shortcode
            },
        }

        response = requests.post(
            f"{settings.HAKIKISHA_BASE_URL}/mpesa/b2c/hakikisha/v1/hakikisha",
            headers=headers,
            json=payload,
        )
        print("After token resp", response.text)
        json_resp = response.json()
        return response.status_code, json_resp
