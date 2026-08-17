import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from core.celery import app
from lock import TaskWithLock
from payouts.models import PayoutRequest
from payouts.processors import QUERYABLE_PROCESSORS

logger = logging.getLogger(__name__)

# How stale a PROCESSING payout must be before we bother querying the provider for its status.
STALE_PAYOUT_MINUTES = 5


@app.task(base=TaskWithLock, name="process_payout_request", queue="payouts", retries=0, time_limit=300)
def process_payout_request(payout_request_id):
    try:
        payout_request = PayoutRequest.objects.get(id=payout_request_id)
        payout_request.send()
    except PayoutRequest.DoesNotExist:
        logger.error(f"PayoutRequest with id {payout_request_id} does not exist.")
    except Exception as e:
        logger.error(f"Error processing payout request: {str(e)}", exc_info=True)
        raise e


@app.task(name="query_pending_payouts", queue="payouts", retries=0, time_limit=120)
def query_pending_payouts():
    """Find PROCESSING payouts older than STALE_PAYOUT_MINUTES, for any provider/country
    combo that supports status polling (see payouts.processors.QUERYABLE_PROCESSORS), and
    dispatch a status query for each."""
    if not QUERYABLE_PROCESSORS:
        return

    queryable = Q()
    for provider, country in QUERYABLE_PROCESSORS:
        queryable |= Q(provider=provider, country=country)

    cutoff = timezone.now() - timedelta(minutes=STALE_PAYOUT_MINUTES)
    stale_ids = PayoutRequest.objects.filter(
        queryable,
        status="PROCESSING",
        created_at__lte=cutoff,
    ).values_list("id", flat=True)

    for payout_id in stale_ids:
        query_payout_status.apply_async(args=[payout_id])


@app.task(base=TaskWithLock, name="query_payout_status", queue="payouts", retries=0, time_limit=60)
def query_payout_status(payout_request_id):
    try:
        payout_request = PayoutRequest.objects.get(id=payout_request_id)
        payout_request.query_status()
    except PayoutRequest.DoesNotExist:
        logger.error(f"PayoutRequest with id {payout_request_id} does not exist.")
    except Exception as e:
        logger.error(f"Error querying payout status: {str(e)}", exc_info=True)
        raise e


def _result_parameters(result):
    """Flatten a Result's ResultParameters.ResultParameter list into a {Key: Value} dict."""
    items = (result.get("ResultParameters") or {}).get("ResultParameter") or []
    return {item.get("Key"): item.get("Value") for item in items}


@app.task(name="process_mpesa_payout_callback", queue="payout_results")
def process_mpesa_payout_callback(payload):
    try:
        result = payload.get("Result")
        if not result:
            raise Exception(f"Result object not found in payload: {payload}")

        tracking_id = result.get("OriginatorConversationID")
        tracking_id_2 = result.get("ConversationID")
        result_code = result.get("ResultCode")
        message = result.get("ResultDesc")

        # Ordinary B2C/B2B payment results carry the original send()'s conversation id
        # pair (tracking_id/tracking_id_2); TransactionStatusQuery results carry the
        # query's own pair (query_tracking_id/query_tracking_id_2) instead - see
        # PayoutRequest.query_status().
        payout_req = PayoutRequest.objects.filter(
            Q(tracking_id=tracking_id, tracking_id_2=tracking_id_2)
            | Q(query_tracking_id=tracking_id, query_tracking_id_2=tracking_id_2)
        ).first()
        if not payout_req:
            raise Exception(f"PayoutRequest with tracking_id {tracking_id} or {tracking_id_2} not found.")

        if payout_req.status == "SUCCESS":
            logger.info(f"PayoutRequest with tracking_id {tracking_id} has already been processed successfully.")
            return

        params = _result_parameters(result)
        transaction_status = params.get("TransactionStatus")

        if transaction_status is not None:
            # This is the async result of a TransactionStatusQuery (dispatched from
            # query_pending_payouts), not a normal B2C/B2B payment result - ResultCode
            # here only reflects whether the *query* was processed, not whether the
            # underlying payout succeeded, so it must not drive SUCCESS/FAILED directly.
            payout_req.callback_response = result
            status_text = str(transaction_status).strip().lower()

            if "complet" in status_text:
                payout_req.provider_reference = params.get("ReceiptNo") or payout_req.provider_reference
                payout_req.message = message
                payout_req.status = "SUCCESS"
                payout_req.save()
                payout_req.complete()
            elif any(keyword in status_text for keyword in ("fail", "revers", "cancel", "reject")):
                # Only an explicit failure signal from the provider triggers a refund -
                # we never guess with money already debited from the wallet in send().
                payout_req.message = message
                payout_req.status = "FAILED"
                payout_req.save()
                payout_req.close_on_failure()
            else:
                # Inconclusive - leave PROCESSING. Either a later poll resolves it, or
                # PayoutRequest.QUERY_REVIEW_MINUTES elapses and it's flagged for manual review.
                payout_req.save()
            return

        provider_reference = result.get("TransactionID")
        payout_req.provider_reference = provider_reference
        payout_req.callback_response = result
        payout_req.message = message

        if result_code != 0:
            if result_code ==  1:
                payout_req.message = "Internal error. Please contact support."
            payout_req.status = "FAILED"
            payout_req.save()
            payout_req.close_on_failure()
            return

        payout_req.status = "SUCCESS"
        payout_req.save()
        payout_req.complete()

    except Exception as e:
        logger.error(f"Error processing MPESA payout callback: {str(e)}", exc_info=True)


def validate_b2c_number(payload):

    from payouts.processors.mpesa import MpesaHakikisha

    hakikisha = MpesaHakikisha()
    hakikisha.validate_account(payload)