import logging

from decimal import Decimal

from django.db import models
from django.db import transaction as db_transaction


from callbacks.tasks import send_callback_notification
from common import AliasModel
from constants import CURRENCIES, DEPOSIT_COUNTRIES_CHOICES
from pricing.models import PAYOUT_PROVIDER_CHOICES
from user_accounts.models import Business
from validators import ALPHANUMERIC_ONLY
from wallet.models import Wallet

logger = logging.getLogger(__name__)

class PayoutRequest(AliasModel):

    STATUS_CHOICES = [
        ("PENDING", "PENDING"),
        ("PROCESSING", "PROCESSING"),
        ("IN_REVIEW", "IN REVIEW"),
        ("SUCCESS", "SUCCESS"),
        ("FAILED", "FAILED"),
    ]

    business = models.ForeignKey(Business, on_delete=models.PROTECT, related_name="payout_requests")
    country = models.CharField(max_length=3, choices=DEPOSIT_COUNTRIES_CHOICES, default="KE")
    currency = models.CharField(max_length=3, default="KES", choices=CURRENCIES)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    charge = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    taxes = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    phone_number = models.CharField(max_length=20,)
    reference = models.CharField(max_length=255, blank=True, null=True, validators=[ALPHANUMERIC_ONLY])
    narration = models.TextField(blank=True, null=True, validators=[ALPHANUMERIC_ONLY])
    provider = models.CharField(choices=PAYOUT_PROVIDER_CHOICES, max_length=20, blank=True, null=True)  # e.g. MPESA-C2B
    provider_reference = models.CharField(max_length=255, blank=True, null=True, validators=[ALPHANUMERIC_ONLY])
    tracking_id = models.CharField(max_length=100, blank=True, null=True)
    tracking_id_2 = models.CharField(max_length=100, blank=True, null=True)
    init_response = models.JSONField(blank=True, null=True)
    callback_response = models.JSONField(blank=True, null=True)
    message = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PO_{self.alias_id}"

    @property
    def total_amount(self):
        return self.amount + self.charge + self.taxes

    def send(self):
        with db_transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(business=self.business, currency=self.currency)
            tx = wallet.debit(Decimal(self.total_amount), reference=f"PAY_{self.alias}", trans_type="PAYOUT", description=f"Payout for {self.alias}")
            try:
                if self.provider == "MPESA-B2C":
                    from .processors import MpesaB2CProcessor
                    processor = MpesaB2CProcessor()
                    self.phone_number = processor.validate_phone_number(self.phone_number)
                    payload = {
                        "amount": self.amount,
                        "phone_number": self.phone_number,
                        "reference": f"PO_{self.alias}",
                        "remarks": self.narration or f"Payout for PO_{self.alias}"
                    }
                    status_code, response = processor.b2c_send(payload)

                    if status_code not in range(200, 300):
                        self.status = "FAILED"
                        self.message = response.get("errorMessage", "Unknown error")
                        self.save()
                        self.close_on_failure(response)
                        return response

                    self.init_response = response
                    self.tracking_id = response.get("OriginatorConversationID")
                    self.tracking_id_2 = response.get("ConversationID")
                    self.message = response.get("ResponseDescription")
                    self.status = "PROCESSING"

                    if response.get("ResponseCode") != "0":
                        self.status = "FAILED"
                        self.save()
                        self.close_on_failure(response)
                        return

                    self.save()
                    return response

            except Wallet.DoesNotExist:
                self.status = "FAILED"
                self.message = "No wallet found for the specified currency."
                self.save()
                return {"error": "No wallet found for the specified currency."}

            except ValueError as ve:
                self.status = "FAILED"
                self.message = str(ve)
                self.save()
                self.close_on_failure(response)
                return {"error": str(ve)}

            except Exception as e:
                logger.error(f"Error processing payout request {self.alias}: {str(e)}", exc_info=True)
                self.status = "IN_REVIEW"
                self.message = str("Unknown error occurred while processing payout.")
                self.save()
                return {"error": str(e)}

    def close_on_failure(self, response=None):
        with db_transaction.atomic():
            business = self.business
            wallet = Wallet.objects.select_for_update().get(business=business, currency=self.currency)
            trans = wallet.credit(self.total_amount, reference=f"PAY_REFUND_{self.alias}", trans_type="REFUND", description=f"Refund for failed payout {self.alias}")
            db_transaction.on_commit(lambda: send_callback_notification.apply_async(args=[self.id, "PAYOUT",], ))

    def complete(self):
        send_callback_notification.apply_async(args=[self.id, "PAYOUT",])
