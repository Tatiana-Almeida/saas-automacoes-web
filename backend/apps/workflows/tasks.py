from celery import shared_task
import time


@shared_task
def execute_workflow(workflow_id, input_data=None):
    time.sleep(2)
    return {"workflow_id": workflow_id, "status": "executed"}
