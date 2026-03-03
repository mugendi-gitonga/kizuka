import base64
import datetime
import logging
import os, json
from django.conf import settings
import requests
from requests.auth import HTTPBasicAuth

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from OpenSSL import crypto
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

logger = logging.getLogger(__name__)

class MpesaC2BProcessor():

    def __init__(self):
        self.consumerKey = settings.MPESA_CONSUMER_KEY
        self.consumerSecret = settings.MPESA_CONSUMER_SECRET

    def pass_encryptor(self):

        initiator_password = settings.INITIATOR_PASSWORD
        initiator_password = bytes(initiator_password, "utf_8")

        f = open(BASE_DIR / "ProductionCertificate.cer", "r")
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

    def get_mpesa_token(self):
        url = (
            f"{settings.MPESA_BASE_API_URL}/oauth/v1/generate?grant_type=client_credentials"
        )
        resp = requests.get(
            url, auth=HTTPBasicAuth(self.consumerKey, self.consumerSecret), timeout=60
        )
        if not resp.status_code == 200:
            raise Exception(resp.text)

        access_token = resp.json().get("access_token")
        expires_in = resp.json().get("expires_in")
        return access_token

    def send_stk_push(self, phone_number, amount, reference, description=""):
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            password = base64.b64encode(
                f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode("utf-8")
            ).decode("utf-8")

            token = self.get_mpesa_token(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET)
            headers = {"Authorization": f"Bearer {token}"}

            payload = {
                "BusinessShortCode": settings.MPESA_SHORTCODE,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": settings.MPESA_TRANS_TYPE,
                "Amount": amount,
                "PartyA": phone_number,
                "PartyB": (
                    settings.MPESA_PARTY_B
                    if settings.MPESA_PARTY_B
                    else settings.MPESA_SHORTCODE
                ),
                "PhoneNumber": phone_number,
                "CallBackURL": f'{settings.APP_URL}/payment/stkpush/confirmation/',
                "AccountReference": reference,
                "TransactionDesc": description if description else f"for {reference}",
            }
            # return payload
            url = f"{settings.MPESA_BASE_API_URL}/mpesa/stkpush/v1/processrequest"
            resp = requests.post(url, json=payload, headers=headers)
            json_resp = resp.json()
            return resp.status_code, json_resp
        except requests.exceptions.ReadTimeout as ex:
            error = f"Timeout error for deposit: {self.reference} > {self.invoice.account}: {ex}"
            logger.error(error, exc_info=True)

        except Exception as ex:
            logger.error(ex, exc_info=True)

    def query_status(self, CheckoutRequestID):

        url = f"{settings.MPESA_BASE_API_URL}/mpesa/stkpushquery/v1/query"
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(
            f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode("utf-8")
        ).decode("utf-8")

        payload = {
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": CheckoutRequestID,  # STK_PUSH request ID from response
        }

        token = self.get_mpesa_token(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET)
        headers = {"Authorization": f"Bearer {token}"}

        resp = requests.post(url, json=payload, headers=headers)
        json_resp = resp.json()
        print(json_resp)
        return json_resp
