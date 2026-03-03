import logging

from django.db import models
from django.db import transaction as db_transaction
from dns.transaction import Transaction

from common import AliasModel


logger = logging.getLogger(__name__)
# Create your models here.

class Wallet(AliasModel):
    business = models.OneToOneField("user_accounts.Business", on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    can_withdraw = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business.name}-{self.balance}"

    def credit(self, amount, reference, trans_type, description=None):
        tx_exists = Transaction.objects.filter(reference=reference).exists()
        if reference and tx_exists:
            logger.warning(f"A transaction with reference {reference} already exists.")
            return

        with db_transaction.atomic():
            self.balance += amount
            self.save()

            tx = Transaction.objects.create(
                wallet=self,
                amount=amount,
                trans_type=trans_type,
                reference=reference,
                description=description,
            )
            logger.info(f"Wallet credited with {amount}. New balance: {self.balance}. Transaction reference: {reference}")
            return tx
    
    def debit(self, amount, reference, trans_type, description=None):
        if self.balance < amount:
            logger.warning(f"Insufficient balance for debit of {amount}. Current balance: {self.balance}")
            raise ValueError("Insufficient balance")

        tx_exists = Transaction.objects.filter(reference=reference).exists()
        if reference and tx_exists:
            logger.warning(f"A transaction with reference {reference} already exists.")
            return

        with db_transaction.atomic():
            self.balance -= amount
            self.save()

            tx = Transaction.objects.create(
                wallet=self,
                amount=amount,  
                trans_type=trans_type,
                reference=reference,
                description=description,
            )
            logger.info(f"Wallet debited with {amount}. New balance: {self.balance}. Transaction reference: {reference}")
            return tx


class Transaction(AliasModel):

    T_TYPES = [
        ("DEPOSIT", "DEPOSIT"),
        ("PAYOUT", "PAYOUT"),
        ("REFUND", "REFUND"),
        ("WITHDRAWAL", "WITHDRAWAL"),
        ("FEE", "FEE"),
        ("TAX", "TAX"),
        ("ADJUSTMENT", "ADJUSTMENT"),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    trans_type = models.CharField(max_length=20, choices=T_TYPES)  # e.g. DEPOSIT, WITHDRAWAL
    reference = models.CharField(max_length=255, blank=True, null=True, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
