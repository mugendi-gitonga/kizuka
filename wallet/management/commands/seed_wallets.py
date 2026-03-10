from django.core.management.base import BaseCommand
from django.db import transaction
from constants import CURRENCIES
from wallet.models import Wallet
from user_accounts.models import Business


class Command(BaseCommand):
    help = "Seed wallets for all businesses based on available currencies in constants.py"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing wallets (delete and recreate)',
        )

    def handle(self, *args, **options):
        force_recreate = options.get('force', False)

        # Get currencies from constants.py
        if not CURRENCIES:
            self.stdout.write(self.style.WARNING('No currencies defined in constants.py'))
            return

        currencies = [currency[0] for currency in CURRENCIES]
        self.stdout.write(
            self.style.SUCCESS(f'Found {len(currencies)} active currencies: {", ".join(currencies)}')
        )

        # Get all businesses
        businesses = Business.objects.all()
        if not businesses.exists():
            self.stdout.write(self.style.WARNING('No businesses found in the database'))
            return

        self.stdout.write(
            self.style.SUCCESS(f'Found {businesses.count()} businesses')
        )

        # Seed wallets
        created_count = 0
        skipped_count = 0
        deleted_count = 0

        with transaction.atomic():
            for business in businesses:
                for currency in currencies:
                    wallet_exists = Wallet.objects.filter(
                        business=business,
                        currency=currency
                    ).exists()

                    if wallet_exists:
                        if force_recreate:
                            # Delete and recreate
                            Wallet.objects.filter(
                                business=business,
                                currency=currency
                            ).delete()
                            Wallet.objects.create(
                                business=business,
                                currency=currency,
                                balance=0.00,
                                can_withdraw=True
                            )
                            deleted_count += 1
                            created_count += 1
                            self.stdout.write(
                                f'  ✓ Recreated wallet: {business.name} ({currency})'
                            )
                        else:
                            skipped_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f'  ✗ Skipped existing wallet: {business.name} ({currency})'
                                )
                            )
                    else:
                        # Create new wallet
                        Wallet.objects.create(
                            business=business,
                            currency=currency,
                            balance=0.00,
                            can_withdraw=True
                        )
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ Created wallet: {business.name} ({currency})')
                        )

        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS(f'Wallet Seeding Complete'))
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count} wallets'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count} wallets'))
        if deleted_count > 0:
            self.stdout.write(self.style.WARNING(f'Recreated: {deleted_count} wallets'))
        self.stdout.write('=' * 70 + '\n')
