import requests
import json
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

def get_zoho_access_token():
    """Exchange the permanent Refresh Token for a temporary Access Token"""
    cache_key = "zoho_access_token"
    token = cache.get(cache_key)

    if not token:
        # No token in cache, let's refresh
        url = "https://accounts.zoho.com/oauth/v2/token"
        params = {
            "refresh_token": settings.ZOHO_REFRESH_TOKEN,
            "client_id": settings.ZOHO_CLIENT_ID,
            "client_secret": settings.ZOHO_CLIENT_SECRET,
            "grant_type": "refresh_token",
        }
        response = requests.post(url, params=params)
        data = response.json()

        token = data.get("access_token")
        # Zoho tokens last 3600s. Cache for 3500s to be safe.
        if token:
            cache.set(cache_key, token, timeout=3000)

    return token


def send_zoho_message_api(to_email, subject, content):
    try:
        """Send email via Zoho Messages API (REST)"""
        access_token = get_zoho_access_token()
        # Your Zoho Account ID (usually your email or a numeric ID found in Zoho Mail settings)
        account_id = settings.ZOHO_ACCOUNT_ID
        url = f"https://mail.zoho.com/api/accounts/{account_id}/messages"

        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "fromAddress": f"Kizuka Support <{settings.EMAIL_HOST_USER}>",
            "toAddress": to_email,
            "subject": subject,
            "content": content,
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code != 200:
            logger.error(f"Failed to send email via Zoho API: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending email via Zoho API: {str(e)}", exc_info=True)
        return False
