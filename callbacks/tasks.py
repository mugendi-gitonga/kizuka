import logging
import requests
from core.celery import app
from callbacks.models import BusinessCallback, CallbackLog


@app.task(name="send_callback_notification_task", queue="callback_tasks")
def send_callback_notification(item_id, event_type):
    from payins.models import DepositRequest
    from payouts.models import PayoutRequest
    from callbacks.serializers import DepositCallbackSerializer, PayoutCallbackSerializer

    try:
        callback = None
        payload = None
        if event_type == "PAYIN":
            item = DepositRequest.objects.get(id=item_id)
            business = item.business
            callback = BusinessCallback.objects.filter(business=business, event_type=event_type).first()
            payload = DepositCallbackSerializer(item).data
        elif event_type == "PAYOUT":
            item = PayoutRequest.objects.get(id=item_id)
            business = item.business
            callback = BusinessCallback.objects.filter(business=business, event_type=event_type).first()
            payload = PayoutCallbackSerializer(item).data
        else:
            logging.error(f"Invalid event type: {event_type}")
            return

        if (callback and callback.callback_url and payload):
            response = requests.post(callback.callback_url, json=payload, timeout=10)
            response.raise_for_status()  # Raise an error for bad status codes
            logging.info(f"Successfully sent callback notification to {callback.callback_url} for business {business.name}")
            # Log the callback response
            CallbackLog.objects.create(
                callback=callback,
                payload=payload,
                response_status=response.status_code,
                response_body=response.text
            )   
    except Exception as e:
        logging.error(f"Error sending callback notification: {str(e)}", exc_info=True)

        status_code = 0  # 0 or 599 are common 'internal/network error' placeholders
        response_body = str(e)

        if hasattr(e, "response") and e.response is not None:
            status_code = e.response.status_code
            response_body = e.response.text
        elif isinstance(e, requests.exceptions.ConnectionError):
            # DNS failure, Refused connection, etc.
            status_code = 502  # Bad Gateway is the most accurate proxy
        elif isinstance(e, requests.exceptions.Timeout):
            status_code = 504  # Gateway Timeout

        CallbackLog.objects.create(
            callback=callback,
            payload=payload,
            response_status=status_code,
            response_body=response_body,
            success=False,
        )
