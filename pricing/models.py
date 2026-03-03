import logging

from decimal import Decimal

from django.db import models

from common import AliasModel
from constants import DEPOSIT_COUNTRIES_CHOICES
from validators import ALPHANUMERIC_ONLY, NUMERIC_ONLY


logger = logging.getLogger(__name__)
# Create your models here.

PLAN_TYPES = [
    ("PERCENTAGE", "PERCENTAGE"),
    ("TIERED", "TIERED")
]

CURRENCIES = [
    ("KES", "KES"),
    # ("UGX", "UGX"),
    # ("TZS", "TZS"),
    # ("ZMW", "ZMW"),
]

PROVIDER_CHOICES = [
    ("MPESA-C2B", "MPESA-C2B"),
    ("MPESA-B2C", "MPESA-B2C"),
    ("MPESA-B2B", "MPESA-B2B"),
]


class PricingPlan(models.Model):
    name = models.CharField(max_length=45, validators=[ALPHANUMERIC_ONLY,],)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    currency = models.CharField(
        max_length=3,
        choices=CURRENCIES,
        blank=True,
        null=True,
        help_text="Required for XB payments",
    )
    country = models.CharField(max_length=3, choices=DEPOSIT_COUNTRIES_CHOICES)
    tarrif_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PricingCharge(models.Model):
    tarrif = models.ForeignKey(PricingPlan, on_delete=models.CASCADE, related_name="charges")
    min_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2)
    charge = models.DecimalField(max_digits=10, decimal_places=2)
    is_percentage = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class BusinessPricingPlan(models.Model):
    business = models.ForeignKey("user_accounts.Business", on_delete=models.CASCADE, related_name="tarrifs")
    plan = models.ForeignKey(PricingPlan, on_delete=models.CASCADE, related_name="businesses")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tarrif"
        unique_together = ("plan", "business")

    @classmethod
    def calculate_charge(cls, business, provider, amount, currency):
        try:
            subscription = cls.objects.filter(business=business, plan__provider=provider, plan__currency=currency).select_related("plan").first()
            if not subscription:
                raise ValueError(f"No pricing plan found for business {business.id} with provider {provider} and currency {currency}")
            
            if subscription.plan.tarrif_type == "PERCENTAGE":
                charge = subscription.plan.charges.filter(country=business.country, min_amount__lte=amount, max_amount__gte=amount).first()
                if charge:
                    return charge.charge if not charge.is_percentage else Decimal((charge.charge / 100) * amount)
            elif subscription.plan.tarrif_type == "TIERED":
                charge = subscription.plan.charges.filter(country=business.country, min_amount__lte=amount, max_amount__gte=amount).first()
                if charge:
                    return Decimal(charge.charge)
            return None
        except Exception as e:
            logger.error(f"Error calculating charge for business {business.id} and provider {provider}: {str(e)}", exc_info=True)


    @classmethod
    def seed_business_plans(cls, business):
        try:
            default_plans = PricingPlan.objects.filter(default=True)
            for plan in default_plans:
                cls.objects.get_or_create(business=business, plan=plan)
        except Exception as e:
            logger.error(f"Error seeding pricing plans for business {business.id}: {str(e)}", exc_info=True)


class CountryTax(models.Model):
    country = models.CharField(max_length=3, choices=DEPOSIT_COUNTRIES_CHOICES, unique=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def compute_tax(cls, country, amount):
        try:
            tax = cls.objects.filter(country=country).first()
            if tax:
                return Decimal((tax.tax_percentage / 100) * amount)
            return Decimal(0)
        except Exception as e:
            logger.error(f"Error computing tax for country {country} and amount {amount}: {str(e)}", exc_info=True)
