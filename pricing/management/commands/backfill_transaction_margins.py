from django.core.management.base import BaseCommand
from django.db import transaction

from payins.models import DepositRequest
from payouts.models import PayoutRequest
from pricing.models import TransactionMargin


class Command(BaseCommand):
    help = (
        "Backfill TransactionMargin records for successful deposits/payouts that predate "
        "this feature (the post_save signal only records new ones going forward)."
    )

    def handle(self, *args, **options):
        deposits = DepositRequest.objects.filter(
            status="SUCCESS", wallet_credited=True, margin__isnull=True
        )
        payouts = PayoutRequest.objects.filter(status="SUCCESS", margin__isnull=True)

        deposit_count = 0
        payout_count = 0
        error_count = 0

        with transaction.atomic():
            for deposit in deposits:
                try:
                    if TransactionMargin.record_for_deposit(deposit):
                        deposit_count += 1
                except Exception as e:
                    error_count += 1
                    self.stderr.write(self.style.ERROR(f"  ✗ Deposit {deposit.alias_id}: {e}"))

            for payout in payouts:
                try:
                    if TransactionMargin.record_for_payout(payout):
                        payout_count += 1
                except Exception as e:
                    error_count += 1
                    self.stderr.write(self.style.ERROR(f"  ✗ Payout {payout.alias_id}: {e}"))

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('Transaction Margin Backfill Complete'))
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'Deposit margins created: {deposit_count}'))
        self.stdout.write(self.style.SUCCESS(f'Payout margins created: {payout_count}'))
        if error_count:
            self.stdout.write(self.style.ERROR(f'Errors: {error_count}'))
        self.stdout.write('=' * 80 + '\n')
