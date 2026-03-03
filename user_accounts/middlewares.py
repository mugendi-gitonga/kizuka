from django.conf import settings
from importlib import import_module
from django.utils.deprecation import MiddlewareMixin
from optimize import get_business
from .models import UserSession

engine = import_module(settings.SESSION_ENGINE)


class PreventConcurrentLoginsMiddleware(MiddlewareMixin):
    """
    Django middleware that prevents multiple concurrent logins..
    Adapted from http://stackoverflow.com/a/1814797 and https://gist.github.com/peterdemin/5829440
    """

    def process_request(self, request):
        if request.user.is_authenticated:
            key_from_cookie = request.session.session_key
            if hasattr(request.user, "user_session"):
                saved_key = request.user.user_session.session_key
                if saved_key != key_from_cookie:
                    # Delete the Session object from database and cache
                    engine.SessionStore(saved_key).delete()
                    request.user.user_session.session_key = key_from_cookie
                    request.user.user_session.save()
            else:
                UserSession.objects.create(
                    user=request.user, session_key=key_from_cookie
                )


class MultisiteAccountHandler(MiddlewareMixin):
    """Returns user active account

    Args:
        MiddlewareMixin (class): Django middleware mixin
    """

    def process_request(self, request):
        request.business = get_business(request) or None
