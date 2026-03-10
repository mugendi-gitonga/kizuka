import logging
from decimal import Decimal

from django.db.models import Q

from core.celery import app
from payouts.models import PayoutRequest

logger = logging.getLogger(__name__)


@app.task(name="process_payout_request", queue="payouts", retries=0, time_limit=300)
def process_payout_request(payout_request_id):
    try:
        payout_request = PayoutRequest.objects.get(id=payout_request_id)
        payout_request.send()
    except PayoutRequest.DoesNotExist:
        logger.error(f"PayoutRequest with id {payout_request_id} does not exist.")
    except Exception as e:
        logger.error(f"Error processing payout request: {str(e)}", exc_info=True)
        raise e


@app.task(name="process_mpesa_payout_callback", queue="payout_results")
def process_mpesa_payout_callback(payload):

    try:
        result = payload.get("Result")
        if not result:
            raise Exception(f"Result object not found in payload: {payload}")

        tracking_id = result.get("OriginatorConversationID")
        tracking_id_2 = result.get("ConversationID")
        provider_reference = result.get("TransactionID")
        result_code = result.get("ResultCode")
        message = result.get("ResultDesc")

        payout_req = PayoutRequest.objects.filter(tracking_id=tracking_id, tracking_id_2=tracking_id_2).first()
        if not payout_req:
            raise Exception(f"PayoutRequest with tracking_id {tracking_id} or {tracking_id_2} not found.")

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

        payout_req.status = "COMPLETED"
        payout_req.save()
        payout_req.complete()

    except Exception as e:
        logger.error(f"Error processing MPESA payout callback: {str(e)}", exc_info=True)
