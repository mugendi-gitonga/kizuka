from django.db import models

from common import AliasModel


class BusinessCallback(AliasModel):
    EVENT_TYPES = [
        ("PAYIN", "PAYIN"),
        ("PAYOUT", "PAYOUT"),
    ]

    business = models.ForeignKey("user_accounts.Business", on_delete=models.CASCADE, related_name="callbacks")
    event_type = models.CharField(max_length=7, choices=EVENT_TYPES)
    callback_url = models.URLField(max_length=255, blank=True, null=True) 
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('business', 'event_type')

    def __str__(self):
        return f"{self.business.name} - {self.event_type}"
    

class CallbackLog(AliasModel):
    callback = models.ForeignKey(BusinessCallback, on_delete=models.CASCADE, related_name="logs")
    payload = models.JSONField()
    response_status = models.IntegerField()
    response_body = models.TextField()
    success = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Log for {self.callback.business.name} - {self.callback.event_type} at {self.created_at}"


class WhitelistedIP(AliasModel):
    """Whitelisted IP addresses for callback requests"""
    business = models.ForeignKey("user_accounts.Business", on_delete=models.CASCADE, related_name="whitelisted_ips")
    ip_address = models.GenericIPAddressField()
    description = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('business', 'ip_address')
        verbose_name = "Whitelisted IP"
        verbose_name_plural = "Whitelisted IPs"

    def __str__(self):
        return f"{self.business.name} - {self.ip_address}"


