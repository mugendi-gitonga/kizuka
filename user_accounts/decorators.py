from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from .models import Business, BusinessTeamMember
from django.core.exceptions import PermissionDenied


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


def require_business_role(allowed_roles=["admin", "staff"]):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Get the business ID from the URL (e.g., /dashboard/<uuid:business_id>/)
            business = request.business

            if not business:
                raise PermissionDenied("Business context missing.")

            # 2. Check if this user has an active, non-archived membership
            membership = BusinessTeamMember.objects.filter(
                user=request.user,
                business=business,
                is_active=True,
                archived=False,
            ).first()

            # 3. Validate membership and role
            if not membership or membership.role not in allowed_roles:
                raise PermissionDenied(
                    "You do not have the required role for this business."
                )

            # 4. Inject membership into request for easy access in the view
            request.business_membership = membership
            request.current_business = membership.business

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
