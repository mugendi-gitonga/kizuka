from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from constants import DEPOSIT_COUNTRIES_CHOICES
from pricing.models import CountryTax


class Command(BaseCommand):
    help = "Seed country tax rates"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing country tax rates',
        )

    def handle(self, *args, **options):
        force_recreate = options.get('force', False)

        # Define tax configurations
        tax_configs = self._get_tax_configs()

        if not tax_configs:
            self.stdout.write(self.style.WARNING('No tax configurations defined'))
            return

        self.stdout.write(
            self.style.SUCCESS(f'Seeding {len(tax_configs)} country tax configurations')
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for config in tax_configs:
                country = config['country']
                tax_percentage = config['tax_percentage']

                # Check if tax exists
                tax_exists = CountryTax.objects.filter(country=country).exists()

                if tax_exists:
                    if force_recreate:
                        # Update existing tax
                        CountryTax.objects.filter(country=country).update(
                            tax_percentage=tax_percentage
                        )
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Updated tax: {country} = {tax_percentage}%'
                            )
                        )
                    else:
                        skipped_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ✗ Skipped existing tax: {country} = {tax_percentage}%'
                            )
                        )
                else:
                    # Create new tax
                    CountryTax.objects.create(
                        country=country,
                        tax_percentage=tax_percentage
                    )
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Created tax: {country} = {tax_percentage}%')
                    )

        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('Country Tax Seeding Complete'))
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count} tax rates'))
        self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count} tax rates'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count} tax rates'))
        self.stdout.write('=' * 70 + '\n')

    def _get_tax_configs(self):
        """
        Define tax configurations per country
        
        KE (Kenya): 5% tax on M-Pesa deposits (MPESA-C2B)
        """
        return [
            {
                'country': 'KE',
                'tax_percentage': Decimal('5')
            },
            {
                'country': 'UG',
                'tax_percentage': Decimal('0')
            },
            {
                'country': 'TZ',
                'tax_percentage': Decimal('0')
            },
            {
                'country': 'ZM',
                'tax_percentage': Decimal('0')
            },
        ]
