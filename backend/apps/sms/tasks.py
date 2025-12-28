import time

from celery import shared_task


@shared_task
def send_sms_message(to, message):
    time.sleep(1)
    return {"to": to, "message": message, "status": "sent"}
