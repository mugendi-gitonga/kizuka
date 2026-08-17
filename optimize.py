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
                # Staff/admin accounts (e.g. superusers) aren't business owners -
                # don't phantom-provision a business for them just because they hit a page.
                if user.is_staff:
                    return None
                # Keyed on the unique email/username rather than first_name, which is
                # frequently blank or shared across users and collides with Business.name's
                # unique constraint (was raising an unhandled IntegrityError on every request).
                business, created = get_business_model().objects.get_or_create(
                    owner=user, defaults={"name": f"{user.username}'s Business"}
                )
                if created:
                    business.team_members.create(user=user, role="admin", is_active=True)
                return business
            return biz.business
