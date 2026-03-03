import logging
import requests
from core.celery import app
from callbacks.models import BusinessCallback, CallbackLog


@app.task(name="send_callback_notification_task", queue="callback_tasks")
def send_callback_notification(item_id, event_type):
    from payins.models import DepositRequest
    from callbacks.serializers import DepositCallbackSerializer

    try:
        callback_url = None
        payload = None
        if event_type == "PAYIN":
            item = DepositRequest.objects.get(id=item_id)
            business = item.business
            callback_url = BusinessCallback.objects.filter(business=business, event_type=event_type).first()
            payload = DepositCallbackSerializer(item).data
        elif event_type == "PAYOUT":
            # Handle payout retrieval if needed
            # item = PayoutRequest.objects.get(id=item_id)
            # business = item.business
            # callback_url = BusinessCallback.objects.filter(business=business, event_type=event_type).first()
            # payload = PayoutCallbackSerializer(item).data
            pass
        else:
            logging.error(f"Invalid event type: {event_type}")
            return

        if (callback_url and callback_url.url and payload):
            response = requests.post(callback_url.url, json=payload, timeout=10)
            response.raise_for_status()  # Raise an error for bad status codes
            logging.info(f"Successfully sent callback notification to {callback_url.url} for business {business.name}")
            # Log the callback response
            CallbackLog.objects.create(
                callback=callback_url,
                payload=payload,
                response_status=response.status_code,
                response_body=response.text
            )   
    except Exception as e:
        logging.error(f"Error sending callback notification: {str(e)}", exc_info=True)
