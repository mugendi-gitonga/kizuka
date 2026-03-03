import logging
from django.conf import settings
from rest_framework import authentication
from rest_framework import exceptions

from user_accounts.models import Business
from utils import encrypt

from django.conf import settings

logger = logging.getLogger(__name__)


class APITokenAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = 'Invalid token header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)

        elif len(auth) > 2:
            msg = 'Invalid token header. Bearer string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)
        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = 'Invalid token header. Bearer string should not contain invalid characters.'
            raise exceptions.AuthenticationFailed(msg)

        if "token" not in token:
            return None

        try:
            if settings.ENVIRONMENT == "live":
                _ = token.split("tokenLive")[1]
            else:
                _ = token.split("tokenTest")[1]
        except Exception:
            environment = settings.ENVIRONMENT
            raise exceptions.AuthenticationFailed(f"Invalid token for {environment} environment")

        return self.authenticate_credentials(request,token)
    
    def authenticate_credentials(self, request, key):
        encrypted_key = encrypt(key)
        businesses = Business.objects.filter(api_key=encrypted_key)
        if businesses.count() > 1:
            logger.error(f"API key issue with token: {key} - returned multiple businesses including {businesses}")
            raise exceptions.AuthenticationFailed("Failed - API Key issue. Contact customer support")
        business = businesses.first()
        if not business:
            raise exceptions.AuthenticationFailed("Invalid api token")
        request.business = business

        user = business.owner
        if not user.is_active:
            raise exceptions.AuthenticationFailed("User inactive or deleted")
        return (user, business)