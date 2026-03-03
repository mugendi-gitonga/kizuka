from django.shortcuts import get_object_or_404, redirect
from functools import wraps
from .models import Business, BusinessTeamMember


def business_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Fetch the business
        business = request.business

        # 2. Check Permission: Owner OR Active Admin
        is_owner = request.user == business.owner
        is_admin = BusinessTeamMember.objects.filter(
            business=business, user=request.user, role="admin", is_active=True
        ).exists()

        if not (is_owner or is_admin):
            return redirect("dashboard_overview")

        # 3. Pass the business object to the view so you don't have to fetch it again
        return view_func(request, *args, **kwargs)

    return _wrapped_view
