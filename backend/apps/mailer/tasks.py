import time

from celery import shared_task


@shared_task
def send_email_message(to, subject, body):
    # Placeholder: integrate with email provider
    time.sleep(1)
    return {"to": to, "subject": subject, "status": "sent"}
