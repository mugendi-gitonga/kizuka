import logging

from decimal import ROUND_HALF_UP, ROUND_UP, Decimal

from django.db import models

from common import AliasModel
from constants import CURRENCIES, DEPOSIT_COUNTRIES_CHOICES
from validators import ALPHANUMERIC_ONLY, NUMERIC_ONLY
from exceptions import UserAdviceException, LimitsExceededException


logger = logging.getLogger(__name__)
# Create your models here.

PLAN_TYPES = [
    ("PERCENTAGE", "PERCENTAGE"),
    ("TIERED", "TIERED")
]

PROVIDER_CHOICES = [
    ("MPESA-C2B", "MPESA-C2B"),
]

PAYOUT_PROVIDER_CHOICES = [
    ("MPESA-B2C", "MPESA-B2C"),
    ("MPESA-B2B", "MPESA-B2B"),
]


class PricingPlan(models.Model):
    name = models.CharField(max_length=45, validators=[ALPHANUMERIC_ONLY,],)
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES+PAYOUT_PROVIDER_CHOICES)
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

    def __str__(self):
        return f"{self.provider} - {self.currency}"


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
    def calculate_charge(cls, business, provider, amount, currency, country):
        try:
            subscription = cls.objects.filter(business=business, plan__provider=provider, plan__currency=currency, plan__country=country).select_related("plan").first()
            if not subscription:
                raise ValueError(f"No pricing plan found for business {business.id} with provider {provider} and currency {currency}")
            
            if subscription.plan.tarrif_type == "PERCENTAGE":
                charge = subscription.plan.charges.filter(min_amount__lte=amount, max_amount__gte=amount).first()
                if charge:
                    return charge.charge if not charge.is_percentage else Decimal((charge.charge / 100) * amount).quantize(Decimal("0.01"), rounding=ROUND_UP)
            elif subscription.plan.tarrif_type == "TIERED":
                charge = subscription.plan.charges.filter(min_amount__lte=amount, max_amount__gte=amount).first()
                if charge:
                    result = Decimal(charge.charge)
                    return result.quantize(Decimal("0.01"), rounding=ROUND_UP)
            return 0
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
                result = Decimal((tax.tax_percentage / 100) * amount)
                return result.quantize(Decimal("0.01"), rounding=ROUND_UP)
            return Decimal(0)
        except Exception as e:
            logger.error(f"Error computing tax for country {country} and amount {amount}: {str(e)}", exc_info=True)


class ProviderCostPlan(models.Model):
    """What a payment provider charges us per transaction - the mirror of PricingPlan,
    which is what we charge the business. Not tied to any business: the provider charges
    the same fee regardless of which business's customer triggered the transaction."""

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES + PAYOUT_PROVIDER_CHOICES)
    currency = models.CharField(max_length=3, choices=CURRENCIES, default="KES")
    country = models.CharField(max_length=3, choices=DEPOSIT_COUNTRIES_CHOICES, default="KE")
    is_free = models.BooleanField(default=False, help_text="No cost tiers needed - always 0 (e.g. MPESA-C2B)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Provider Cost Plan"
        unique_together = ("provider", "currency", "country")

    def __str__(self):
        return f"{self.provider} cost - {self.currency}"

    @classmethod
    def calculate_cost(cls, provider, amount, currency, country):
        try:
            plan = cls.objects.filter(provider=provider, currency=currency, country=country).first()
            if not plan:
                logger.warning(f"No provider cost plan found for provider {provider}, currency {currency}, country {country}")
                return Decimal("0.00")

            if plan.is_free:
                return Decimal("0.00")

            tier = plan.tiers.filter(min_amount__lte=amount, max_amount__gte=amount).first()
            if tier:
                return Decimal(tier.charge).quantize(Decimal("0.01"), rounding=ROUND_UP)
            return Decimal("0.00")
        except Exception as e:
            logger.error(f"Error calculating provider cost for provider {provider}: {str(e)}", exc_info=True)
            return Decimal("0.00")


class ProviderCostTier(models.Model):
    plan = models.ForeignKey(ProviderCostPlan, on_delete=models.CASCADE, related_name="tiers")
    min_amount = models.DecimalField(max_digits=10, decimal_places=2)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2)
    charge = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Provider Cost Tier"


class TransactionMargin(models.Model):
    """Internal-only record of revenue vs. provider cost for one successful deposit/payout,
    created by a signal (see pricing/signals.py) once the source transaction completes -
    kept in its own table, never serialized to businesses, so it can't leak via the API."""

    EVENT_TYPES = [
        ("PAYIN", "PAYIN"),
        ("PAYOUT", "PAYOUT"),
    ]

    event_type = models.CharField(max_length=7, choices=EVENT_TYPES)
    deposit = models.OneToOneField("payins.DepositRequest", on_delete=models.CASCADE, related_name="margin", null=True, blank=True)
    payout = models.OneToOneField("payouts.PayoutRequest", on_delete=models.CASCADE, related_name="margin", null=True, blank=True)
    business = models.ForeignKey("user_accounts.Business", on_delete=models.CASCADE, related_name="transaction_margins")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES + PAYOUT_PROVIDER_CHOICES)
    currency = models.CharField(max_length=3, choices=CURRENCIES)
    amount = models.DecimalField(max_digits=20, decimal_places=2, help_text="The transaction amount")
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="What we charged the business")
    provider_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="What the provider charged us")
    margin = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="revenue - provider_cost")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Transaction Margin"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(deposit__isnull=False, payout__isnull=True)
                    | models.Q(deposit__isnull=True, payout__isnull=False)
                ),
                name="margin_exactly_one_of_deposit_or_payout",
            )
        ]

    def __str__(self):
        return f"{self.event_type} margin - {self.provider} - {self.margin}"

    @classmethod
    def record_for_deposit(cls, deposit):
        """Create the margin row for a successful deposit, if one doesn't already exist.
        Shared by the post_save signal (new transactions) and the backfill command
        (existing transactions from before this feature existed)."""
        if cls.objects.filter(deposit=deposit).exists():
            return None

        business = deposit.business
        provider_cost = cls._provider_cost(deposit)
        revenue = deposit.charge or 0
        return cls.objects.create(
            event_type="PAYIN",
            deposit=deposit,
            business=business,
            provider=deposit.provider,
            currency=deposit.currency,
            amount=deposit.amount,
            revenue=revenue,
            provider_cost=provider_cost,
            margin=revenue - provider_cost,
        )

    @classmethod
    def record_for_payout(cls, payout):
        """Create the margin row for a successful payout, if one doesn't already exist."""
        if cls.objects.filter(payout=payout).exists():
            return None

        business = payout.business
        provider_cost = cls._provider_cost(payout)
        revenue = payout.charge or 0
        return cls.objects.create(
            event_type="PAYOUT",
            payout=payout,
            business=business,
            provider=payout.provider,
            currency=payout.currency,
            amount=payout.amount,
            revenue=revenue,
            provider_cost=provider_cost,
            margin=revenue - provider_cost,
        )

    @staticmethod
    def _provider_cost(instance):
        return ProviderCostPlan.calculate_cost(instance.provider, instance.amount, instance.currency, instance.country)


class AccountLimits(models.Model):
    """Set and control limits per account"""

    label = models.SlugField(unique=True, help_text="Limit identifier e.g low-risk")
    currency = models.CharField(max_length=3, choices=CURRENCIES)
    collection_amount_per_txn = models.DecimalField(decimal_places=2, max_digits=11)
    disbursement_amount_per_txn = models.DecimalField(decimal_places=2, max_digits=11)
    disbursement_amount_per_day = models.DecimalField(decimal_places=2, max_digits=11)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.label

    @property
    def collection_description(self):
        return f"Max {self.currency} {self.collection_amount_per_txn}/transaction"

    @property
    def disbursement_description(self):
        return f"Max {self.currency} {self.disbursement_amount_per_txn}/transaction ({self.currency} {self.disbursement_amount_per_day}/day)"

    class Meta:
        verbose_name = "Account Limit"


class BusinessAccountLimits(models.Model):
    business = models.ForeignKey(
        "user_accounts.Business", related_name="account_limits", on_delete=models.CASCADE
    )
    account_limit = models.ForeignKey(
        AccountLimits, related_name="business_account_limits", on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = "Business Account Limit"

    @classmethod
    def can_collect(cls, business, amount, currency):
        """Check if business can collect more funds"""
        record = BusinessAccountLimits.objects.get(
            business=business, account_limit__currency=currency
        )
        if Decimal(amount) > Decimal(record.account_limit.collection_amount_per_txn):
            raise UserAdviceException(
                f"The maximum amount allowed for this transaction is {record.account_limit.currency} {record.account_limit.collection_amount_per_txn}. Please adjust the amount and try again."
            )
        return True

    @classmethod
    def can_disburse(cls, business, amount, wallet):
        """Check if business can disburse more funds"""
        currency = wallet.currency
        record = BusinessAccountLimits.objects.get(
            business=business, account_limit__currency=currency
        )
        if Decimal(amount) > Decimal(record.account_limit.disbursement_amount_per_txn):
            raise LimitsExceededException(
                f"The maximum amount allowed for this transaction is {currency} {record.account_limit.disbursement_amount_per_txn}. Please adjust the amount and try again."
            )

        # Check if transaction has passed the daily limit
        current_day_paid_out = wallet.daily_payout
        current_daily_limit = record.account_limit.disbursement_amount_per_day
        if current_day_paid_out > current_daily_limit:
            raise LimitsExceededException(
                f"Completing this transaction will pass your daily limit of {currency} {current_daily_limit}. Your current day payout total is {currency} {current_day_paid_out}"
            )
        return True

    @classmethod
    def save_limits(cls, business):
        volume_kes_limit = AccountLimits.objects.get(label="default-volume-kes")

        BusinessAccountLimits.objects.get_or_create(business=business, account_limit=volume_kes_limit)
