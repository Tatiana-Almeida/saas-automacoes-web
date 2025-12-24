from typing import Any, Dict

TENANT_CREATED = 'TenantCreated'
USER_CREATED = 'UserCreated'
PLAN_UPGRADED = 'PlanUpgraded'

# Helper to emit events via Celery

def emit_event(event_name: str, payload: Dict[str, Any]):
    from .tasks import handle_event
    handle_event.delay(event_name, payload)
