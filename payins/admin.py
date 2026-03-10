from django.contrib import admin

from payins.models import DepositRequest
from pricing.models import BusinessPricingPlan, CountryTax

# Register your models here.

def mark_as_completed(modeladmin, request, queryset):
    """Admin action to mark selected deposit requests as completed"""
    updated_count = 0
    for deposit in queryset:
        try:
            if deposit.status in ["PENDING", "PROCESSING"]:
                deposit.status = "SUCCESS"
                deposit.paid_amount = deposit.amount  # Assuming full amount is paid for simplicity, adjust as needed
                # Get charges
                charges = BusinessPricingPlan.calculate_charge(
                    deposit.business, "MPESA-C2B", deposit.amount, deposit.currency, deposit.country
                )
                deposit.charge = charges if charges else 0
                # Get Taxes
                deposit.taxes = CountryTax.compute_tax(deposit.country, deposit.amount)
                # Get net amount
                deposit.net_amount = deposit.paid_amount - (deposit.charge + deposit.taxes)
                deposit.save()

                deposit.refresh_from_db()  # Ensure we have the latest data
                deposit.complete()  # Call the method to handle completion logic
                updated_count += 1
            elif deposit.status == "SUCCESS" and not deposit.wallet_credited:
                # If already marked as SUCCESS but wallet not credited, try to credit it
                deposit.complete()
                updated_count += 1
        except Exception as e:
            modeladmin.message_user(request, f"Error processing deposit {deposit.id}: {str(e)}", level="error")
    modeladmin.message_user(request, f"{updated_count} deposit request(s) marked as completed.")
mark_as_completed.short_description = "Mark selected deposit requests as completed"


def mark_as_failed(modeladmin, request, queryset):
    """Admin action to mark selected deposit requests as failed"""
    updated_count = 0
    for deposit in queryset:
        if deposit.status in ["PENDING", "PROCESSING"]:
            deposit.status = "FAILED"
            deposit.save()
            deposit.complete()
            updated_count += 1
    modeladmin.message_user(request, f"{updated_count} deposit request(s) marked as failed.")
mark_as_failed.short_description = "Mark selected deposit requests as failed"


@admin.register(DepositRequest)
class DepositRequestAdmin(admin.ModelAdmin):
    list_display = ("alias_id", "amount", "paid_amount", "net_amount", "status", "created_at")
    list_filter = ("status", "provider", "created_at")
    search_fields = ("reference", "narration", "phone_number", "alias_id", "provider_reference")
    actions = [mark_as_completed]
