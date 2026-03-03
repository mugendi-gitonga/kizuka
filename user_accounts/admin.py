from django.contrib import admin
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

