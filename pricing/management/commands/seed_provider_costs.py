from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from pricing.models import ProviderCostPlan, ProviderCostTier


class Command(BaseCommand):
    help = "Seed provider cost plans and tiers - what payment providers charge us (not what we charge businesses)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing provider cost plans and tiers',
        )

    def handle(self, *args, **options):
        force_recreate = options.get('force', False)
        configs = self._get_cost_configs()

        self.stdout.write(self.style.SUCCESS(f'Seeding {len(configs)} provider cost configurations'))

        created_plans = 0
        skipped_plans = 0
        created_tiers = 0
        skipped_tiers = 0

        with transaction.atomic():
            for config in configs:
                provider = config['provider']
                currency = config['currency']
                country = config['country']
                is_free = config['is_free']
                tiers = config['tiers']

                plan, plan_created = ProviderCostPlan.objects.get_or_create(
                    provider=provider,
                    currency=currency,
                    country=country,
                    defaults={'is_free': is_free},
                )

                if plan_created:
                    created_plans += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Created plan: {provider} ({currency}/{country})'))
                else:
                    skipped_plans += 1
                    if force_recreate and plan.is_free != is_free:
                        plan.is_free = is_free
                        plan.save(update_fields=['is_free'])
                    self.stdout.write(self.style.WARNING(f'  ✗ Existing plan: {provider} ({currency}/{country})'))

                for tier_config in tiers:
                    tier_exists = ProviderCostTier.objects.filter(
                        plan=plan,
                        min_amount=tier_config['min_amount'],
                        max_amount=tier_config['max_amount'],
                    ).exists()

                    if tier_exists:
                        if force_recreate:
                            ProviderCostTier.objects.filter(
                                plan=plan,
                                min_amount=tier_config['min_amount'],
                                max_amount=tier_config['max_amount'],
                            ).update(charge=tier_config['charge'])
                            created_tiers += 1
                        else:
                            skipped_tiers += 1
                    else:
                        ProviderCostTier.objects.create(
                            plan=plan,
                            min_amount=tier_config['min_amount'],
                            max_amount=tier_config['max_amount'],
                            charge=tier_config['charge'],
                        )
                        created_tiers += 1

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('Provider Cost Seeding Complete'))
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'Created Plans: {created_plans}'))
        self.stdout.write(self.style.WARNING(f'Skipped Plans: {skipped_plans}'))
        self.stdout.write(self.style.SUCCESS(f'Created/Updated Tiers: {created_tiers}'))
        self.stdout.write(self.style.WARNING(f'Skipped Tiers: {skipped_tiers}'))
        self.stdout.write('=' * 80 + '\n')

    def _build_tiers(self, tiers):
        return [
            {
                'min_amount': Decimal(str(min_amount)),
                'max_amount': Decimal(str(max_amount)),
                'charge': Decimal(str(charge)),
            }
            for min_amount, max_amount, charge in tiers
        ]

    def _get_cost_configs(self):
        """
        Provider cost tariffs (what Safaricom charges us, not what we charge businesses):

        MPESA-C2B: free.
        MPESA-B2C: "Business" column of the B2C-to-registered-users tariff (Customer column is always 0).
        MPESA-B2B: the B2B tariff.
        """
        mpesa_b2c_cost_tiers = [
            (1, 49, 0),
            (50, 100, 0),
            (101, 500, 5),
            (501, 1000, 5),
            (1001, 1500, 5),
            (1501, 2500, 9),
            (2501, 3500, 9),
            (3501, 5000, 9),
            (5001, 7500, 11),
            (7501, 10000, 11),
            (10001, 15000, 11),
            (15001, 20000, 11),
            (20001, 25000, 13),
            (25001, 30000, 13),
            (30001, 35000, 13),
            (35001, 40000, 13),
            (40001, 45000, 13),
            (45001, 50000, 13),
            (50001, 70000, 13),
            (70001, 250000, 13),
        ]

        mpesa_b2b_cost_tiers = [
            (1, 49, 2),
            (50, 100, 3),
            (101, 500, 8),
            (501, 1000, 13),
            (1001, 1500, 18),
            (1501, 2500, 25),
            (2501, 3500, 30),
            (3501, 5000, 39),
            (5001, 7500, 48),
            (7501, 10000, 54),
            (10001, 15000, 63),
            (15001, 20000, 68),
            (20000, 25000, 74),
            (25001, 30000, 79),
            (30001, 35000, 90),
            (35001, 40000, 106),
            (40001, 45000, 110),
            (45001, 50000, 115),
            (50001, 70000, 115),
            (70001, 150000, 115),
            (150001, 250000, 115),
            (250001, 500000, 115),
            (500001, 1000000, 115),
            (1000001, 3000000, 115),
            (3000001, 5000000, 115),
            (5000001, 20000000, 115),
            (20000001, 50000000, 115),
        ]

        return [
            {
                'provider': 'MPESA-C2B',
                'currency': 'KES',
                'country': 'KE',
                'is_free': True,
                'tiers': [],
            },
            {
                'provider': 'MPESA-B2C',
                'currency': 'KES',
                'country': 'KE',
                'is_free': False,
                'tiers': self._build_tiers(mpesa_b2c_cost_tiers),
            },
            {
                'provider': 'MPESA-B2B',
                'currency': 'KES',
                'country': 'KE',
                'is_free': False,
                'tiers': self._build_tiers(mpesa_b2b_cost_tiers),
            },
        ]
