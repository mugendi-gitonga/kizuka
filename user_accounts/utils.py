import hashlib
import hmac
import secrets

from django.conf import settings


def hash_token(token):
    """Hash a token using SHA256"""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token, token_hash):
    """Verify a token against its hash using constant-time comparison"""
    return secrets.compare_digest(hash_token(token), token_hash)


def generate_otp_code(length=6):
    """Generate a cryptographically secure numeric OTP code"""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp_code(code):
    """Hash an OTP code keyed on SECRET_KEY.

    A plain SHA256 (as used for high-entropy reset/invite tokens) is brute-forceable
    offline in seconds for a 6-digit code if the DB ever leaks, so this is keyed
    with SECRET_KEY instead of hash_token's unkeyed hash.
    """
    return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def verify_otp_code(code, code_hash):
    """Verify an OTP code against its hash using constant-time comparison"""
    return secrets.compare_digest(hash_otp_code(code), code_hash)
