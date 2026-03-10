from django.contrib import admin
from django.db import transaction as db_transaction

from payouts.models import PayoutRequest

# Register your models here.
def mark_as_completed(modeladmin, request, queryset):
    """Admin action to mark selected payout requests as completed"""
    updated_count = 0
    for payout in queryset:
        if payout.status in ["PENDING", "PROCESSING", "IN_REVIEW"]:
            payout.status = "SUCCESS"
            payout.save()
            payout.complete()  # Call the method to handle completion logic
            updated_count += 1
    modeladmin.message_user(request, f"{updated_count} payout request(s) marked as completed.")
mark_as_completed.short_description = "Mark selected Requests Successful"


def mark_as_failed(modeladmin, request, queryset):
    """Admin action to mark selected payout requests as failed"""
    updated_count = 0
    for payout in queryset:
        if payout.status in ["PENDING", "PROCESSING", "IN_REVIEW"]:
            with db_transaction.atomic():
                payout.status = "FAILED"
                payout.save()
                payout.close_on_failure()  # Call the method to handle failure logic
                updated_count += 1
    modeladmin.message_user(request, f"{updated_count} payout request(s) marked as failed.")
mark_as_failed.short_description = "Mark Selected Requests Failed"


@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "provider", "amount", "currency", "country", "status", "created_at")
    list_filter = ("status", "provider", "currency", "country")
    search_fields = ("business__name", "provider", "amount")
    ordering = ("-created_at",)
    actions = [mark_as_completed, mark_as_failed]
