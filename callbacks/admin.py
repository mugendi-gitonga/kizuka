from django.contrib import admin

from callbacks.models import BusinessCallback, CallbackLog, WhitelistedIP


# Register your models here.
@admin.register(WhitelistedIP)
class WhitelistedIPAdmin(admin.ModelAdmin):
    list_display = ("business", "ip_address", "is_active", "created_at", "updated_at")
    search_fields = ("business__name", "ip_address")
    list_filter = ("is_active",)


@admin.register(BusinessCallback)
class BusinessCallbackAdmin(admin.ModelAdmin):
    list_display = ("business", "event_type", "callback_url", "is_active", "created_at", "updated_at")
    search_fields = ("business__name", "callback_url")
    list_filter = ("event_type", "is_active")


@admin.register(CallbackLog)
class CallbackLogAdmin(admin.ModelAdmin):
    list_display = ("callback", "response_status", "success", "created_at")
    search_fields = ("callback__business__name",)
    list_filter = ("success", "created_at")