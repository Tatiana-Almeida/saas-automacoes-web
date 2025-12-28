# ruff: noqa: E501
from typing import Any, Dict

from apps.auditing.models import AuditLog
from django.db import connection


def _safe_audit_create(**kwargs):
    """Ensure audit entries are written to the public schema.

    Some listeners may be executed while the DB search_path is set to a
    tenant-only schema, which hides shared/public tables. Force the
    connection to use the public schema while creating AuditLog records.
    """
    # Best-effort: perform a schema-qualified INSERT into the public
    # auditing table so listeners can record events even when
    # connection.search_path is set to a tenant schema.
    try:
        import json

        from django.utils import timezone

        table = AuditLog._meta.db_table
        sql = f'INSERT INTO public."{table}" ("user_id", "path", "method", "source", "action", "status_code", "tenant_schema", "tenant_id", "ip_address", "created_at", "payload") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING "id"'
        params = (
            kwargs.get("user").id if kwargs.get("user") else None,
            kwargs.get("path"),
            kwargs.get("method"),
            kwargs.get("source"),
            kwargs.get("action"),
            kwargs.get("status_code"),
            kwargs.get("tenant_schema"),
            kwargs.get("tenant_id"),
            kwargs.get("ip_address"),
            timezone.now(),
            (
                json.dumps(kwargs.get("payload"))
                if kwargs.get("payload") is not None
                else None
            ),
        )
        with connection.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()[0]
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        # Fall back to ORM attempt; if this fails, propagate so callers
        # can handle or tests can assert accordingly.
        return AuditLog.objects.create(**kwargs)


# Listener implementations per event


def on_tenant_created(payload: Dict[str, Any]):
    # Minimal side-effect: record an audit entry in the public schema
    _safe_audit_create(
        user=None,
        path="/events/TenantCreated",
        method="EVENT",
        source="events",
        action="event_TenantCreated",
        status_code=200,
        tenant_schema=payload.get("tenant_schema"),
        tenant_id=payload.get("tenant_id"),
        ip_address=None,
    )


def on_user_created(payload: Dict[str, Any]):
    _safe_audit_create(
        user=None,
        path="/events/UserCreated",
        method="EVENT",
        source="events",
        action="event_UserCreated",
        status_code=200,
        tenant_schema=payload.get("tenant_schema"),
        tenant_id=payload.get("tenant_id"),
        ip_address=None,
    )


def on_plan_upgraded(payload: Dict[str, Any]):
    _safe_audit_create(
        user=None,
        path="/events/PlanUpgraded",
        method="EVENT",
        source="events",
        action="event_PlanUpgraded",
        status_code=200,
        tenant_schema=payload.get("tenant_schema"),
        tenant_id=payload.get("tenant_id"),
        ip_address=None,
    )


LISTENER_REGISTRY = {
    "TenantCreated": on_tenant_created,
    "UserCreated": on_user_created,
    "PlanUpgraded": on_plan_upgraded,
    # Stripe webhook-derived events
    "StripeInvoicePaid": lambda payload: _safe_audit_create(
        user=None,
        path="/events/StripeInvoicePaid",
        method="EVENT",
        source="events",
        action="event_StripeInvoicePaid",
        status_code=200,
        tenant_schema=payload.get("tenant_schema"),
        tenant_id=payload.get("tenant_id"),
        ip_address=None,
        payload={"stripe": payload.get("stripe")},
    ),
    "StripeSubscriptionUpdated": lambda payload: _safe_audit_create(
        user=None,
        path="/events/StripeSubscriptionUpdated",
        method="EVENT",
        source="events",
        action="event_StripeSubscriptionUpdated",
        status_code=200,
        tenant_schema=payload.get("tenant_schema"),
        tenant_id=payload.get("tenant_id"),
        ip_address=None,
        payload={"stripe": payload.get("stripe")},
    ),
    "StripeEvent": lambda payload: _safe_audit_create(
        user=None,
        path="/events/StripeEvent",
        method="EVENT",
        source="events",
        action="event_StripeEvent",
        status_code=200,
        tenant_schema=payload.get("tenant_schema"),
        tenant_id=payload.get("tenant_id"),
        ip_address=None,
        payload={"stripe": payload.get("stripe")},
    ),
    # Generic webhook receipt event
    "WebhookReceived": lambda payload: _safe_audit_create(
        user=None,
        path="/events/WebhookReceived",
        method="EVENT",
        source="events",
        action="event_WebhookReceived",
        status_code=200,
        tenant_schema=payload.get("tenant_schema"),
        tenant_id=payload.get("tenant_id"),
        ip_address=None,
        payload={
            "provider": payload.get("provider"),
            "payload": payload.get("payload"),
        },
    ),
}
