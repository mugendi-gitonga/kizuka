from django.contrib import admin

from wallet.models import Transaction, Wallet

# Register your models here.

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("business", "balance", "currency", "created_at", "updated_at")
    search_fields = ("business__name",)
    list_filter = ("currency",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "amount", "trans_type", "created_at")
    search_fields = ("wallet__business__name",)
    list_filter = ("trans_type",)