import zoneinfo
from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from importlib import import_module
from django.utils.deprecation import MiddlewareMixin
from optimize import get_business
from .models import UserSession

engine = import_module(settings.SESSION_ENGINE)


class TimezoneMiddleware(MiddlewareMixin):
    """Activates the browser-reported timezone (set via the `tzname` cookie, see base.html) for this request."""

    def process_request(self, request):
        tzname = request.COOKIES.get("tzname")
        if tzname:
            try:
                timezone.activate(zoneinfo.ZoneInfo(unquote(tzname)))
                return
            except zoneinfo.ZoneInfoNotFoundError:
                pass
        timezone.deactivate()


class EnforceInactivityLogoutMiddleware(MiddlewareMixin):
    """Force-logs out dashboard users after INACTIVITY_LOGOUT_SECONDS of inactivity.

    Only active in the live environment: dev/test would make manual testing and
    automated test suites intermittently fail sessions mid-run.
    """

    EXEMPT_PATH_PREFIXES = (settings.STATIC_URL, settings.MEDIA_URL)

    def process_request(self, request):
        if settings.ENVIRONMENT != "live":
            return
        if not request.user.is_authenticated:
            return
        if request.path.startswith(self.EXEMPT_PATH_PREFIXES):
            return

        now = timezone.now().timestamp()
        last_activity = request.session.get("last_activity")

        if last_activity is not None and now - last_activity > settings.INACTIVITY_LOGOUT_SECONDS:
            logout(request)
            return redirect(f"{reverse('login')}?expired=1&next={request.path}")

        request.session["last_activity"] = now


class ForcePasswordChangeMiddleware(MiddlewareMixin):
    """Forces a user to set a new password before accessing any other page."""

    def process_request(self, request):
        if not request.user.is_authenticated:
            return

        if request.path.startswith("/admin/") or request.path.startswith(settings.STATIC_URL) or request.path.startswith(settings.MEDIA_URL):
            return

        exempt_paths = {reverse("logout"), reverse("force_password_change")}
        if request.path in exempt_paths:
            return

        profile = getattr(request.user, "profile", None)
        if profile and profile.must_change_password:
            return redirect("force_password_change")


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
