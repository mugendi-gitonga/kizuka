from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from .models import Business, UserProfile, PasswordResetLog, InviteUserLog

@admin.register(PasswordResetLog)
class PasswordResetLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'ip_address', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'ip_address')
    readonly_fields = ('created_at', 'user', 'status', 'ip_address', 'user_agent', 'error_message')
    ordering = ('-created_at',)
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(InviteUserLog)
class InviteUserLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'business', 'status', 'ip_address', 'created_at')
    list_filter = ('status', 'created_at', 'business')
    search_fields = ('user__email', 'business__name', 'ip_address')
    readonly_fields = ('created_at', 'user', 'business', 'status', 'ip_address', 'user_agent', 'error_message')
    ordering = ('-created_at',)
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')
    search_fields = ('name', 'owner__email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def add_view(self, request, form_url='', extra_context=None):
        # The bare add form only creates a Business row - it skips the owner
        # User, pricing plan, wallet, account limits, and team-membership rows
        # that a real business needs. Route staff through the full setup flow instead.
        next_url = request.GET.get('next') or reverse('admin:user_accounts_business_changelist')
        return redirect(f"{reverse('admin_create_business')}?next={next_url}")
