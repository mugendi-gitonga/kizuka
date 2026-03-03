from django.core.cache import cache
from jwt.exceptions import ExpiredSignatureError
import logging
import ast
from utils import encrypt
from utils import decode_jwt, encrypt

logger = logging.getLogger(__name__)


def get_business_model():
    from user_accounts.models import Business
    return Business


def get_business(request):
    try:
        user = request.user
        if user.is_authenticated and user.is_active:
            # Otherwise check available session
            KEY = f"BIZ_{request.user.id}"
            business = cache.get(KEY)
            if not business:
                business = user.business_memberships.first().business
                cache.set(KEY, business)
            return business
        else:
            payload = {}
            try:
                bytes_request_data = getattr(request, "_body", request.body)
                if bytes_request_data:
                    payload = ast.literal_eval(bytes_request_data.decode("utf-8"))
            except Exception as ex:
                logger.debug(f"Failed to decode data: {ex}")

            # Check if API request and return business
            api_secret = request.META.get("HTTP_AUTHORIZATION")

            if api_secret:
                if len(api_secret.split(" ")) > 1:
                    api_secret_token = api_secret.split(" ")[1]
                    if api_secret_token.startswith("tokenLive") or api_secret_token.startswith("tokenTest"):
                        encrypted_key = encrypt(api_secret_token)
                        return get_business_model().objects.get(
                            api_key=encrypted_key
                        )
    except ExpiredSignatureError:
        if user.is_authenticated and user.is_active:
            return request.user.business_memberships.first().business
    except get_business_model().DoesNotExist:
        if user.is_authenticated and user.is_active:
            return request.user.business_memberships.first().business
    except Exception as ex:
        logger.error(ex, exc_info=True)
        if user.is_authenticated and user.is_active:
            biz = request.user.business_memberships.first()
            if not biz:
                business = get_business_model().objects.create(
                    owner=user, name=f"{user.first_name}'s Business"
                )
                business.team_members.create(user=user, role="admin", is_active=True)
                return business    
            return biz.business
