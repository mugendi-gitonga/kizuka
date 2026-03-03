from django.db import models

# Create your models here.

class BusinessCallback(models.Model):
    EVENT_TYPES = [
        ("PAYIN", "PAYIN"),
        ("PAYOUT", "PAYOUT"),
    ]

    business = models.ForeignKey("user_accounts.Business", on_delete=models.CASCADE, related_name="callbacks")
    event_type = models.CharField(max_length=7, choices=EVENT_TYPES)
    callback_url = models.URLField(max_length=255, blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business.name} - {self.event_type} "
    

class CallbackLog(models.Model):
    callback = models.ForeignKey(BusinessCallback, on_delete=models.CASCADE, related_name="logs")
    payload = models.JSONField()
    response_status = models.IntegerField()
    response_body = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Log for {self.callback.business.name} - {self.callback.event_type} at {self.created_at}"


