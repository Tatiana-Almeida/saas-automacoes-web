import time

from celery import shared_task


@shared_task
def send_whatsapp_message(to, message):
    # Placeholder: integrate with WhatsApp provider SDK
    # Simulate work
    time.sleep(1)
    return {"to": to, "message": message, "status": "sent"}
