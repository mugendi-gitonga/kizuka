from django.core.management.base import BaseCommand
from django.db import transaction
from user_accounts.models import Business
from pricing.models import BusinessPricingPlan


class Command(BaseCommand):
    help = "Seed existing businesses with default pricing plans"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reassignment of pricing plans to all businesses (removes existing assignments)',
        )

    def handle(self, *args, **options):
        force_reassign = options.get('force', False)
        
        businesses = Business.objects.all()
        
        if not businesses.exists():
            self.stdout.write(self.style.WARNING('No businesses found to seed'))
            return

        self.stdout.write(
            self.style.SUCCESS(f'Seeding {businesses.count()} businesses with pricing plans')
        )

        seeded = 0
        skipped = 0
        
        with transaction.atomic():
            for business in businesses:
                existing_plans = BusinessPricingPlan.objects.filter(business=business)
                
                if existing_plans.exists():
                    if force_reassign:
                        # Delete existing assignments and reseed
                        existing_plans.delete()
                        BusinessPricingPlan.seed_business_plans(business)
                        seeded += 1
                        self.stdout.write(
                            f'  ✓ Reassigned plans to {business.name}'
                        )
                    else:
                        skipped += 1
                        self.stdout.write(
                            self.style.WARNING(f'  ✗ Skipped {business.name} (already has plans)')
                        )
                else:
                    # Seed pricing plans for this business
                    BusinessPricingPlan.seed_business_plans(business)
                    seeded += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Seeded plans for {business.name}')
                    )

        # Summary
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('Business Pricing Plans Seeding Complete'))
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS(f'Seeded: {seeded}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped}'))
        self.stdout.write('=' * 80 + '\n')
