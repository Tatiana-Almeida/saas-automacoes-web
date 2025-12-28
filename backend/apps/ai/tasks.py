import time

from celery import shared_task


@shared_task
def run_ai_inference(model, prompt):
    time.sleep(3)
    return {"model": model, "prompt": prompt, "result": "inference_complete"}
