import time

from celery import shared_task


@shared_task
def send_chatbot_message(bot_id, message, session_id=None):
    time.sleep(1)
    return {"bot_id": bot_id, "message": message, "status": "processed"}
