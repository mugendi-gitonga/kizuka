import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BusinessPricingPlan

logger = logging.getLogger(__name__)


@receiver(post_save, sender='user_accounts.Business')
def link_business_to_pricing_plans(sender, instance, created, **kwargs):
    """
    Signal to automatically link a business to default pricing plans when created.
    This ensures every new business gets the standard pricing plans assigned.
    """
    if created:
        try:
            BusinessPricingPlan.seed_business_plans(instance)
            logger.info(f"Successfully linked business '{instance.name}' to default pricing plans")
        except Exception as e:
            logger.error(
                f"Error linking business '{instance.name}' to pricing plans: {str(e)}",
                exc_info=True
            )
