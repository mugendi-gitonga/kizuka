from django.contrib import admin
from .models import (
    PricingPlan,
    PricingCharge,
    BusinessPricingPlan,
    CountryTax,
    AccountLimits,
    ProviderCostPlan,
    ProviderCostTier,
    TransactionMargin,
)


class PricingChargeInline(admin.TabularInline):
    model = PricingCharge
    extra = 1
    min_num = 1
    max_num = 10
    verbose_name = "Charge"
    verbose_name_plural = "Charges"
    

@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "provider", "country", "currency", "tarrif_type", "default", "created_at")
    list_filter = ("provider", "country", "currency", "tarrif_type", "default")
    search_fields = ("name",)
    ordering = ("-created_at",)
    inlines = [PricingChargeInline]


@admin.register(BusinessPricingPlan)
class BusinessPricingPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "business", "plan")
    list_filter = ()
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(CountryTax)
class CountryTaxAdmin(admin.ModelAdmin):
    list_display = ("id", "country", "tax_percentage", "created_at")
    list_filter = ("country",)
    search_fields = ("country",)
    ordering = ("-created_at",)


class ProviderCostTierInline(admin.TabularInline):
    model = ProviderCostTier
    extra = 1
    min_num = 0
    verbose_name = "Cost Tier"
    verbose_name_plural = "Cost Tiers"


@admin.register(ProviderCostPlan)
class ProviderCostPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "currency", "country", "is_free", "updated_at")
    list_filter = ("provider", "currency", "country", "is_free")
    ordering = ("provider",)
    inlines = [ProviderCostTierInline]


@admin.register(TransactionMargin)
class TransactionMarginAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "business", "provider", "amount", "revenue", "provider_cost", "margin", "created_at")
    list_filter = ("event_type", "provider", "currency")
    search_fields = ("business__name",)
    ordering = ("-created_at",)
    date_hierarchy = "created_at"


@admin.register(AccountLimits)
class AccountLimitsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "label",
        "currency",
        "collection_amount_per_txn",
        "disbursement_amount_per_txn",
        "disbursement_amount_per_day",
    )
    list_filter = ("currency",)
    search_fields = ("currency",)
    ordering = ("-created_at",)
