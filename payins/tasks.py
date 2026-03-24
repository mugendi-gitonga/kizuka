import logging
from decimal import Decimal

from callbacks.tasks import send_callback_notification
from core.celery import app
from lock import TaskWithLock
from pricing.models import BusinessPricingPlan, CountryTax

logger = logging.getLogger(__name__)


@app.task(base=TaskWithLock, name="send_deposit_request_to_provider", queue="deposits", retries=0, time_limit=60)
def send_deposit_request_to_provider(deposit_request_id):
    from .models import DepositRequest
    try:
        deposit_request = DepositRequest.objects.get(id=deposit_request_id)
        deposit_request.send()
    except DepositRequest.DoesNotExist:
        logger.error(f"DepositRequest with id {deposit_request_id} does not exist.")
    except Exception as e:
        logger.error(f"Error sending deposit request to provider: {str(e)}", exc_info=True)
        raise e


@app.task(base=TaskWithLock, name="process_mpesa_c2b_callback", queue="deposits_results")
def process_mpesa_c2b_callback(is_stk, payload):
    from payins.models import DepositRequest
    try:
        if is_stk:
            result_code = payload.get("Body", {}).get("stkCallback", {}).get("ResultCode")
            checkout_request_id = payload.get("Body", {}).get("stkCallback", {}).get("CheckoutRequestID")
            message = payload.get("Body", {}).get("stkCallback", {}).get("ResultDesc")
            metaData = payload.get("Body", {}).get("stkCallback", {}).get("CallbackMetadata", {})
            items = metaData.get("Item", []) if metaData else []

            reference = payload.get("BillRefNumber") or payload.get("ReferenceData", {}).get("ReferenceItem", [{}])[0].get("Value")

            # deposit_request = DepositRequest.objects.filter(reference=reference, provider="MPESA-C2B").first()
            deposit_request = DepositRequest.objects.filter(tracking_id=checkout_request_id, provider="MPESA-C2B").first()
            if not deposit_request:
                raise ValueError(f"No matching DepositRequest found for reference: {reference}")

            if deposit_request.status == "SUCCESS":
                logger.info(f"DepositRequest with reference {reference} has already been processed successfully.")
                return

            if result_code == 0:
                deposit_request.status = "SUCCESS"

                # Save MPESA code
                mpesa_receipt = next(
                    (item for item in items if item["Name"] == "MpesaReceiptNumber"),
                    None,
                )
                deposit_request.provider_reference = (
                    mpesa_receipt.get("Value") if mpesa_receipt else None
                )

                # Get amount
                amount = next(
                    (item for item in items if item["Name"] == "Amount"),
                    None,
                )
                deposit_request.paid_amount = Decimal(amount.get("Value")) if amount else 0

                # Get charges
                charges = BusinessPricingPlan.calculate_charge(
                    deposit_request.business, "MPESA-C2B", deposit_request.amount, deposit_request.currency, deposit_request.country
                )
                deposit_request.charge = charges if charges else 0

                # Get Taxes
                deposit_request.taxes = CountryTax.compute_tax(deposit_request.country, deposit_request.amount)

                # Get net amount
                deposit_request.net_amount = deposit_request.paid_amount - (deposit_request.charge + deposit_request.taxes)
                deposit_request.message = message
                deposit_request.save()
                deposit_request.complete()

            else:
                deposit_request.status = "FAILED"
                deposit_request.message = message
                deposit_request.save()
                send_callback_notification.apply_async(args=[deposit_request.id,"PAYIN",])

            return
    except Exception as e:
        logger.error(f"Error processing MPESA C2B callback: {str(e)}", exc_info=True)
        raise e
