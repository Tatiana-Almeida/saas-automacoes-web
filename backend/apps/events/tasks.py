from celery import shared_task
from typing import Dict, Any
from django.utils import timezone

MAX_RETRIES = 3
RETRY_COUNTDOWN = 5


@shared_task(bind=True, queue='events')
def handle_event(self, event_name: str, payload: Dict[str, Any]):
    from .listeners import LISTENER_REGISTRY
    try:
        handler = LISTENER_REGISTRY.get(event_name)
        if not handler:
            # unknown event, send to DLQ
            dead_letter_event.delay(event_name, payload, reason='unknown_event')
            return {'status': 'unknown'}
        handler(payload)
        return {'status': 'ok'}
    except Exception as e:
        # Retry up to MAX_RETRIES, then DLQ
        if getattr(self.request, 'retries', 0) < MAX_RETRIES:
            raise self.retry(exc=e, countdown=RETRY_COUNTDOWN)
        else:
            dead_letter_event.delay(event_name, payload, reason=str(e))
            return {'status': 'dlq', 'error': str(e)}


@shared_task(queue='dlq')
def dead_letter_event(event_name: str, payload: Dict[str, Any], reason: str = ''):
    # Persist DLQ entry in AuditLog for traceability
    from django.db import connection
    from apps.auditing.models import AuditLog
    try:
        # Try to force DB search_path to public for the audit write.
        try:
            with connection.cursor() as cur:
                cur.execute('SET search_path TO public')
        except Exception:
            # best-effort; continue to ORM attempt
            pass

        # Use a schema-qualified raw insert into public to avoid relying on
        # connection search_path (django-tenants may change it elsewhere).
        try:
            import json
            from django.utils import timezone

            table = AuditLog._meta.db_table
            target_schema = payload.get('tenant_schema') or 'public'
            sql = f'INSERT INTO "{target_schema}"."{table}" ("user_id", "path", "method", "source", "action", "status_code", "tenant_schema", "tenant_id", "ip_address", "created_at", "payload") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING "id"'
            params = (
                None,
                f"/events/DLQ/{event_name}",
                'EVENT',
                'events',
                'event_DLQ',
                500,
                payload.get('tenant_schema'),
                payload.get('tenant_id'),
                None,
                timezone.now(),
                json.dumps(payload),
            )
            with connection.cursor() as cur:
                cur.execute(sql, params)
                _id = cur.fetchone()[0]
        except Exception:
            # Fall back to ORM attempt if raw SQL fails
            AuditLog.objects.create(
                user=None,
                path=f"/events/DLQ/{event_name}",
                method='EVENT',
                source='events',
                action='event_DLQ',
                status_code=500,
                tenant_schema=payload.get('tenant_schema'),
                tenant_id=payload.get('tenant_id'),
                ip_address=None,
                payload=payload,
            )
    except Exception:
        # If persisting the DLQ fails (e.g., migrations missing), ensure the
        # DB transaction is rolled back so the test process can continue.
        try:
            connection.rollback()
        except Exception:
            pass
        return {'status': 'failed_to_store', 'reason': reason}
    return {'status': 'stored', 'reason': reason}
