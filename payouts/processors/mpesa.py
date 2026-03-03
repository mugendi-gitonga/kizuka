import base64
import os, json
from django.conf import settings
import requests
from requests.auth import HTTPBasicAuth

from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from OpenSSL import crypto
from pathlib import Path

from payins.processors.mpesa import get_mpesa_token

BASE_DIR = Path(__file__).resolve().parent.parent


def pass_encryptor():

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


def b2c_send(receiver, amount):

    token = get_mpesa_token(settings.B2C_CONSUMER_KEY, settings.B2C_CONSUMER_SECRET)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    encoded_credential = pass_encryptor()

    payload = json.dumps(
        {
            "InitiatorName": settings.B2C_INITIATOR_NAME,
            "SecurityCredential": encoded_credential,
            "CommandID": "BusinessPayment",
            "Amount": amount,
            "PartyA": settings.B2C_SHORTCODE,
            "PartyB": receiver,
            "Remarks": "Jikwachu Payment",
            "QueueTimeOutURL": f"{settings.APP_URL}/transactions/b2c/queue",
            "ResultURL": f"{settings.APP_URL}/transactions/b2c/result",
            "Occassion": "null",
        }
    )
    print(payload)

    response = requests.post(
        f"{settings.MPESA_BASE_API_URL}/mpesa/b2c/v1/paymentrequest",
        headers=headers,
        data=payload,
    )
    response = json.loads(response.text)
    print(response)
    return response
