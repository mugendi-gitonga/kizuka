import hashlib
import secrets


def hash_token(token):
    """Hash a token using SHA256"""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token, token_hash):
    """Verify a token against its hash using constant-time comparison"""
    return secrets.compare_digest(hash_token(token), token_hash)
