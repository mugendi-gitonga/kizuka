from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from constants import CURRENCIES, DEPOSIT_COUNTRIES_CHOICES
from pricing.models import PricingPlan, PricingCharge, PROVIDER_CHOICES, PLAN_TYPES


class Command(BaseCommand):
    help = "Seed pricing plans and pricing charges for deposits"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing pricing plans and charges',
        )

    def handle(self, *args, **options):
        force_recreate = options.get('force', False)

        # Define pricing plan configurations
        pricing_configs = self._get_pricing_configs()

        if not pricing_configs:
            self.stdout.write(self.style.WARNING('No pricing configurations defined'))
            return

        self.stdout.write(
            self.style.SUCCESS(f'Seeding {len(pricing_configs)} pricing plan configurations')
        )

        created_plans = 0
        skipped_plans = 0
        created_charges = 0
        skipped_charges = 0

        with transaction.atomic():
            for config in pricing_configs:
                plan_name = config['name']
                provider = config['provider']
                currency = config['currency']
                country = config['country']
                tarrif_type = config['tarrif_type']
                default = config['default']
                charges = config['charges']

                # Check if plan exists
                plan_exists = PricingPlan.objects.filter(
                    name=plan_name,
                    provider=provider,
                    currency=currency,
                    country=country
                ).exists()

                if plan_exists:
                    if force_recreate:
                        # Delete existing plan and charges
                        plan = PricingPlan.objects.get(
                            name=plan_name,
                            provider=provider,
                            currency=currency,
                            country=country
                        )
                        plan.delete()
                        plan = PricingPlan.objects.create(
                            name=plan_name,
                            provider=provider,
                            currency=currency,
                            country=country,
                            tarrif_type=tarrif_type,
                            default=default
                        )
                        created_plans += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ Recreated plan: {plan_name} ({provider}/{currency}/{country})'
                            )
                        )
                    else:
                        skipped_plans += 1
                        plan = PricingPlan.objects.get(
                            name=plan_name,
                            provider=provider,
                            currency=currency,
                            country=country
                        )
                        self.stdout.write(
                            self.style.WARNING(
                                f'  ✗ Skipped existing plan: {plan_name} ({provider}/{currency}/{country})'
                            )
                        )
                else:
                    # Create new plan
                    plan = PricingPlan.objects.create(
                        name=plan_name,
                        provider=provider,
                        currency=currency,
                        country=country,
                        tarrif_type=tarrif_type,
                        default=default
                    )
                    created_plans += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Created plan: {plan_name} ({provider}/{currency}/{country})'
                        )
                    )

                # Seed charges for this plan
                for charge_config in charges:
                    charge_exists = PricingCharge.objects.filter(
                        tarrif=plan,
                        min_amount=charge_config['min_amount'],
                        max_amount=charge_config['max_amount']
                    ).exists()

                    if charge_exists:
                        if force_recreate:
                            # Update existing charge
                            PricingCharge.objects.filter(
                                tarrif=plan,
                                min_amount=charge_config['min_amount'],
                                max_amount=charge_config['max_amount']
                            ).update(
                                charge=charge_config['charge'],
                                is_percentage=charge_config['is_percentage']
                            )
                            created_charges += 1
                            self.stdout.write(
                                f'    ✓ Updated charge: {charge_config["min_amount"]}-{charge_config["max_amount"]} = {charge_config["charge"]}'
                            )
                        else:
                            skipped_charges += 1
                    else:
                        # Create new charge
                        PricingCharge.objects.create(
                            tarrif=plan,
                            min_amount=charge_config['min_amount'],
                            max_amount=charge_config['max_amount'],
                            charge=charge_config['charge'],
                            is_percentage=charge_config['is_percentage']
                        )
                        created_charges += 1
                        self.stdout.write(
                            f'    ✓ Created charge: {charge_config["min_amount"]}-{charge_config["max_amount"]} = {charge_config["charge"]}'
                        )

        # Summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('Pricing Plans & Charges Seeding Complete'))
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'Created Plans: {created_plans}'))
        self.stdout.write(self.style.WARNING(f'Skipped Plans: {skipped_plans}'))
        self.stdout.write(self.style.SUCCESS(f'Created/Updated Charges: {created_charges}'))
        self.stdout.write(self.style.WARNING(f'Skipped Charges: {skipped_charges}'))
        self.stdout.write('=' * 80 + '\n')

    def _get_pricing_configs(self):
        """
        Define pricing configurations for different providers and currencies
        
        MPESA-C2B: 3% commission (5% tax handled separately in CountryTax)
        MPESA-B2C: 5% OR 70 KES minimum (whichever is greater)
        MPESA-B2B: 0.8% commission
        """
        return [
            {
                'name': 'Standard KES Deposits',
                'provider': 'MPESA-C2B',
                'currency': 'KES',
                'country': 'KE',
                'tarrif_type': 'PERCENTAGE',
                'default': True,
                'charges': [
                    {
                        'min_amount': Decimal('0.00'),
                        'max_amount': Decimal('99999999.99'),
                        'charge': Decimal('3.00'),
                        'is_percentage': True
                    }
                ]
            },
            {
                'name': 'Standard KES Payouts',
                'provider': 'MPESA-B2C',
                'currency': 'KES',
                'country': 'KE',
                'tarrif_type': 'TIERED',
                'default': True,
                'charges': [
                    {
                        'min_amount': Decimal('10.00'),
                        'max_amount': Decimal('250000.00'),
                        'charge': Decimal('70.00'),
                        'is_percentage': True
                    },
                ]
            },
            {
                'name': 'Standard KES B2B',
                'provider': 'MPESA-B2B',
                'currency': 'KES',
                'country': 'KE',
                'tarrif_type': 'PERCENTAGE',
                'default': True,
                'charges': [
                    {
                        'min_amount': Decimal('0.00'),
                        'max_amount': Decimal('99999999.99'),
                        'charge': Decimal('2.00'),
                        'is_percentage': True
                    }
                ]
            },
        ]
