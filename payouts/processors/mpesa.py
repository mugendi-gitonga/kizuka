import base64
import os, json
import requests

from django.conf import settings

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from OpenSSL import crypto

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

        amount = payload.get("amount")
        receiver = payload.get("phone_number")
        remarks = payload.get("remarks", "Instant Payout")
        reference = payload.get("reference")

        payload = {
            "OriginatorConversationID": reference,
            "InitiatorName": self.initiator_name,
            "SecurityCredential": encoded_credential,
            "CommandID": "PromotionPayment",
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
