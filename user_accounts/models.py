from django.db import models
from django.contrib.auth.models import User, Group
from django.contrib.auth import user_logged_in
from django.db import transaction as db_transaction

from common import AliasModel


class UserProfile(AliasModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=255, blank=True, null=True)
    password_reset_token_hash = models.CharField(max_length=255, blank=True, null=True)
    password_reset_requested_at = models.DateTimeField(blank=True, null=True)
    password_reset_ip = models.GenericIPAddressField(blank=True, null=True)
    password_reset_used = models.BooleanField(default=False)
    invite_token_hash = models.CharField(max_length=255, blank=True, null=True)
    invite_requested_at = models.DateTimeField(blank=True, null=True)
    invite_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}"


class Business(AliasModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_businesses')
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    api_key = models.TextField(blank=True, null=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from utils import secret_key_generator
        if not self.api_key:
            key, key_encrypted = secret_key_generator()
            self.api_key = key_encrypted
        super().save(*args, **kwargs)


class BusinessTeamMember(AliasModel):

    ROLES_CHOICES = (
        ("admin", "Admin"),
        ("staff", "Staff"),
    )

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='team_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_memberships')
    role = models.CharField(max_length=20, choices=ROLES_CHOICES)
    is_active = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('business', 'user')
        verbose_name = 'Business Team Member'
        verbose_name_plural = 'Business Team Members'

    def __str__(self):
        return f"{self.user.username} - {self.business.name} ({self.role})"

    def update_role(self, new_role):
        if new_role not in dict(UserProfile.ROLES_CHOICES):
            raise ValueError("Invalid role")
        self.role = new_role
        self.save(update_fields=['role'])


class PasswordResetLog(AliasModel):
    """Audit log for password reset attempts and completions"""
    
    STATUS_CHOICES = (
        ('requested', 'Reset Requested'),
        ('reset_successful', 'Reset Successful'),
        ('reset_failed', 'Reset Failed'),
        ('token_expired', 'Token Expired'),
        ('token_already_used', 'Token Already Used'),
        ('invalid_token', 'Invalid Token'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_logs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Password Reset Log'
        verbose_name_plural = 'Password Reset Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_status_display()} - {self.created_at}"


class InviteUserLog(AliasModel):
    """Audit log for user invitation attempts and completions"""

    STATUS_CHOICES = (
        ('invited', 'User Invited'),
        ('activation_successful', 'Account Activated'),
        ('activation_failed', 'Activation Failed'),
        ('invitation_declined', 'Invitation Declined'),
        ('token_expired', 'Token Expired'),
        ('token_already_used', 'Token Already Used'),
        ('invalid_token', 'Invalid Token'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invite_logs')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='invite_logs')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Invite User Log'
        verbose_name_plural = 'Invite User Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'business', '-created_at']),
            models.Index(fields=['ip_address', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.business.name} - {self.get_status_display()} - {self.created_at}"


class UserSession(models.Model):
    user = models.OneToOneField(User, null=False, related_name="user_session", on_delete=models.CASCADE,)
    session_key = models.CharField(null=False, max_length=40)
