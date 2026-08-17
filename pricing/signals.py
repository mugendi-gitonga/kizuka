import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import BusinessPricingPlan, TransactionMargin

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


@receiver(post_save, sender='payins.DepositRequest')
def record_deposit_margin(sender, instance, created, **kwargs):
    """Record revenue vs. provider cost once a deposit has fully completed.

    Gated on wallet_credited (not just status == "SUCCESS"): the callback handler saves
    status="SUCCESS" first and calls complete() afterwards in a second save() - charge is
    only populated by the second save, and wallet_credited=True only once complete() has
    finished, so this avoids recording a margin with charge still None.
    """
    if instance.status != "SUCCESS" or not instance.wallet_credited:
        return

    try:
        TransactionMargin.record_for_deposit(instance)
    except Exception as e:
        logger.error(f"Error recording deposit margin for {instance.alias_id}: {str(e)}", exc_info=True)


@receiver(post_save, sender='payouts.PayoutRequest')
def record_payout_margin(sender, instance, created, **kwargs):
    """Record revenue vs. provider cost once a payout succeeds.

    Unlike deposits, charge/taxes are computed at init time (before the payout is even sent),
    so they're already populated by the time status transitions to SUCCESS - a plain status
    check is enough here.
    """
    if instance.status != "SUCCESS":
        return

    try:
        TransactionMargin.record_for_payout(instance)
    except Exception as e:
        logger.error(f"Error recording payout margin for {instance.alias_id}: {str(e)}", exc_info=True)
