import random
import string
import uuid
import phonenumbers
import json
import requests
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from hashids import Hashids
import OpenSSL
from OpenSSL import crypto as OpenSSLCrypto
import base64
import binascii
import jwt
import logging

import datetime
from django.conf import settings
from ipware import get_client_ip as ipware_get_client_ip
from rest_framework.pagination import PageNumberPagination

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

from rest_framework_simplejwt.tokens import RefreshToken

from exceptions import InvalidPhoneNumber

hashids = Hashids(settings.HASH_ID_SECRET, min_length=7,alphabet="A1B2C3D4E5F6G7H8I9J1KLMNPQRSTUVWXYZ")

logger = logging.getLogger(__name__)

def pad_string(string, size):
    return string.ljust(size)[:size].encode()


def encrypt(raw_string, padding_size=256*6):
    cipher = AES.new(pad_string(settings.SECRET_KEY, 32), AES.MODE_ECB)
    raw_string = pad_string(raw_string, padding_size)
    encoded_item = base64.b64encode(cipher.encrypt(raw_string))
    return encoded_item.decode('utf-8')


def decrypt(payload):
    cipher = AES.new(pad_string(settings.SECRET_KEY, 32), AES.MODE_ECB)
    decoded = cipher.decrypt(base64.b64decode(payload))
    return decoded.decode().rstrip()


def encode_id(record_id):
    return hashids.encode(record_id)


def decode_id(record_hash):
    try:
        return hashids.decode(record_hash.upper())[0]
    except Exception as ex:
        return None


def encode_jwt(payload, account_id, reference, expiry=settings.JWT_STANDARD_EXPIRY):
    payload["iss"] = "KizukaApp"
    payload["aud"] = [reference, ]
    payload["iat"] = datetime.datetime.now()
    payload["exp"] = datetime.datetime.now()+datetime.timedelta(seconds=expiry)
    payload["accountID"] = account_id
    payload["reference"] = reference
    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    if isinstance(encoded_jwt, str):
        return encoded_jwt
    server_jwt = encoded_jwt.decode("utf-8")
    return server_jwt


def decode_jwt(jwt_payload, audience_id):
    result = jwt.decode(jwt_payload.encode(
        'utf-8'), settings.SECRET_KEY, verify_signature=True, audience=[audience_id, ], algorithms=['HS256', ])
    return result


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


def generate_unique_username(length=8):
	from django.contrib.auth.models import User
	while True:
		username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
		if not User.objects.filter(username=username).exists():
			return f'user_{username}'


class CryptoHandler():
    def generate_keys(self):
        """
        Returns a private and public key
        """
        key = RSA.generate(2048)
        private_key = key.export_key('PEM')
        public_key = key.publickey().export_key('PEM')
        return private_key, public_key

    def encrypt(self, public_key, message):
        rsa_public_key = RSA.importKey(public_key)
        cipher = PKCS1_v1_5.new(rsa_public_key)
        encrypted_message = cipher.encrypt(message.encode('utf-8'))
        return encrypted_message

    def error_handler(self, error):
        print(error)

    def decrypt(self, private, encrypted_message):
        rsa_private = RSA.importKey(private)
        cipher = PKCS1_v1_5.new(rsa_private)
        message = cipher.decrypt(encrypted_message, self.error_handler)
        return message

    def sign(self, private_key, message):
        pkey = OpenSSLCrypto.load_privatekey(
            OpenSSLCrypto.FILETYPE_PEM, private_key, None)
        sign = OpenSSL.crypto.sign(pkey, message, "sha256")
        return sign.hex()

    def verify(self, public_key, signature, message,  encoding="hex"):
        pkey = OpenSSLCrypto.load_publickey(
            OpenSSLCrypto.FILETYPE_PEM, public_key)
        x509 = OpenSSLCrypto.X509()
        x509.set_pubkey(pkey)
        if encoding == "hex":
            signed = bytes.fromhex(signature)
        else:
            signed = signature
        results = OpenSSL.crypto.verify(x509, signed, message, "sha256")
        return results

    def verify_biometrics_signatures(self, public_key_base64, signature_base64, message):
        try:
            decoded_message= base64.b64decode(message)
            try:
                public_key_der = base64.b64decode(public_key_base64)
            except binascii.Error:
                public_key_der = base64.urlsafe_b64decode(public_key_base64)

            try:
                signature = base64.b64decode(signature_base64)
            except binascii.Error:
                signature = base64.urlsafe_b64decode(signature_base64)

            public_key = serialization.load_der_public_key(public_key_der, backend=default_backend())

            public_key.verify(
                signature,
                decoded_message,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False


def get_client_ip(request):
    # 1. Trust Cloudflare/Proxy headers FIRST if they exist
    # These are usually set by your infrastructure and are hard to spoof if configured correctly
    client_ip = request.headers.get("CF-Connecting-IP") or request.headers.get(
        "True-Client-IP"
    )
    if client_ip:
        return client_ip

    # 2. Use ipware for sophisticated proxy handling
    ip, _ = ipware_get_client_ip(request)

    return ip or request.META.get("REMOTE_ADDR")


def secret_key_generator_service(prefix):
    from user_accounts.models import Business

    key = f"{prefix}{uuid.uuid4()}"
    key_encrypted = encrypt(key)
    exists = Business.objects.filter(api_key=key_encrypted).exists()
    if exists:
        secret_key_generator_service(prefix)
    return key, key_encrypted


def secret_key_generator():
    if settings.ENVIRONMENT.lower() == "live":
        return secret_key_generator_service("tokenLive")
    return secret_key_generator_service("tokenTest")


class StandardPagination(PageNumberPagination):
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'  # Allow the client to set page size
    max_page_size = 100  # Pre


def check_phone_number(phone_number, country='KE'):
    try:
        phone_number = phonenumbers.parse(phone_number, country)
        phone_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164).split("+")[1]
        return phone_number
    except phonenumbers.phonenumberutil.NumberParseException:
        raise InvalidPhoneNumber(f'Invalid phone number provided for {country}')


def send_sms(message, recipient):
	try:
		if settings.ENVIRONMENT == 'live':
			headers = {
				'Content-Type': 'application/json'
			}

			payload = json.dumps({
				"apikey": settings.TEXT_SMS_API_KEY,
				"partnerID": settings.TEXT_SMS_PARTNER_ID,
				"message": message,
				"shortcode": settings.TEXT_SMS_SENDER_ID,
				"mobile": recipient
			})

			response = requests.post('https://sms.textsms.co.ke/api/services/sendsms/', headers=headers, data=payload)
			response = json.loads(response.text)

			info_response = response['responses'][0]
			if info_response['response-description'] == 'Success':
				return 1
			else:
				return 0

		print(message)
	except Exception as ex:
			logger.error(ex, exc_info=True)
