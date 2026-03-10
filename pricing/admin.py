from django.contrib import admin
from .models import (
    PricingPlan,
    PricingCharge,
    BusinessPricingPlan,
    CountryTax
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
