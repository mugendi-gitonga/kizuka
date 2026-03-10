import requests
from decimal import Decimal

from django.db import models
from django.db import transaction as db_transaction

from callbacks.tasks import send_callback_notification
from common import AliasModel
from constants import CURRENCIES, DEPOSIT_COUNTRIES_CHOICES
from pricing.models import PROVIDER_CHOICES
from validators import ALPHANUMERIC_ONLY, NUMERIC_ONLY
from .processors import MpesaC2BProcessor
from wallet.models import Wallet

# Create your models here.

class DepositRequest(AliasModel):

    STATUS_CHOICES = [
        ("PENDING", "PENDING"),
        ("PROCESSING", "PROCESSING"),
        ("SUCCESS", "SUCCESS"),
        ("FAILED", "FAILED"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", editable=False)
    business = models.ForeignKey("user_accounts.Business", on_delete=models.PROTECT, related_name="deposit_requests")
    country = models.CharField(max_length=3, choices=DEPOSIT_COUNTRIES_CHOICES, default="KE")
    currency = models.CharField(max_length=3, default="KES", choices=CURRENCIES)
    phone_number = models.CharField(max_length=20, validators=[NUMERIC_ONLY])
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    taxes = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    reference = models.CharField(max_length=255, blank=True, null=True, validators=[ALPHANUMERIC_ONLY])
    narration = models.CharField(max_length=255, null=True, blank=True, validators=[ALPHANUMERIC_ONLY])
    tracking_id = models.CharField(max_length=255, blank=True, null=True, validators=[ALPHANUMERIC_ONLY])
    init_response = models.JSONField(null=True, blank=True)
    stk_response = models.JSONField(null=True, blank=True)
    callback_response = models.JSONField(null=True, blank=True)
    message = models.CharField(max_length=255, blank=True, null=True)
    provider = models.CharField(choices=PROVIDER_CHOICES, max_length=20, blank=True, null=True)  # e.g. MPESA-C2B
    provider_reference = models.CharField(max_length=255, blank=True, null=True, validators=[ALPHANUMERIC_ONLY])

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"DP_{self.alias_id}"

    def send(self):
        try:
            if self.provider == "MPESA-C2B":
                processor = MpesaC2BProcessor()
                self.phone_number = processor.validate_phone_number(self.phone_number)
                reference = self.business.name[:10].upper()
                status_code, response = processor.send_stk_push(
                    self.phone_number, self.amount, reference, self.narration
                )

                if status_code not in range(200, 300):
                    self.status = "FAILED"
                    self.save()
                    return response

                self.reference = reference
                self.init_response = response
                self.tracking_id = response.get("CheckoutRequestID")
                self.status = "PROCESSING" if response.get("ResponseCode") == "0" else "FAILED"
                self.save()
                return response
        except Exception as e:
            self.status = "FAILED"
            self.save()
            raise e

    def complete(self):
        business = self.business
        wallet = Wallet.objects.select_for_update().get(business=business, currency=self.currency)
        with db_transaction.atomic():
            trans = wallet.credit(self.amount, reference=f"DEP-{self.alias}", trans_type="DEPOSIT", description=f"Deposit of {self.amount} for INV-{self.alias}")
            wallet.debit(self.charge, reference=f"FEE-{self.alias}", trans_type="FEE", description=f"Charge of {self.charge} for deposit INV-{self.alias}")
            if self.taxes:
                wallet.debit(self.taxes, reference=f"TAX-{self.alias}", trans_type="TAX", description=f"Tax of {self.taxes} for deposit INV-{self.alias}")

        db_transaction.on_commit(lambda: send_callback_notification.apply_async(args=[self.id, "PAYIN",]))

    def query_status(self):
        if self.country == "KE" and self.status == "PROCESSING":
            processor = MpesaC2BProcessor()
            checkout_request_id = self.init_response.get("CheckoutRequestID")
            response = processor.query_status(checkout_request_id)
            if response.get("ResponseCode") == "0" and response.get("ResultCode") == 0:
                self.status = "SUCCESS"
            self.stk_response = response
            self.save()
            return response
