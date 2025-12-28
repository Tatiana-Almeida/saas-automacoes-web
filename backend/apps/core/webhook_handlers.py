import logging
from typing import Any, Dict, Optional

from apps.events.events import emit_event
from django.conf import settings
from django.core.cache import cache
from django_redis import get_redis_connection

logger = logging.getLogger("apps.core.webhooks")


def _idempotency_key(provider: str, event_id: str) -> str:
    return f"webhook:{provider}:event:{event_id}"


def check_and_mark_idempotent(provider: str, event_id: Optional[str]) -> bool:
    """Return True if first-seen and mark the event; False if already seen."""
    if not event_id:
        # If no event_id, we cannot guarantee idempotency; treat as first time
        return True
    try:
        conn = get_redis_connection("default")
        key = _idempotency_key(provider, event_id)
        ttl = int(getattr(settings, "WEBHOOK_IDEMPOTENCY_TTL_SECONDS", 86400))
        # SET key NX EX ttl
        created = conn.set(key, 1, ex=ttl, nx=True)
        return bool(created)
    except Exception:
        # Fallback: use Django cache backend if Redis is unavailable (tests).
        try:
            key = _idempotency_key(provider, event_id)
            ttl = int(getattr(settings, "WEBHOOK_IDEMPOTENCY_TTL_SECONDS", 86400))
            added = cache.add(key, 1, timeout=ttl)
            return bool(added)
        except Exception:
            # On failure, do not block processing; assume first time
            return True


def dispatch_webhook(
    provider: str,
    payload: Dict[str, Any],
    tenant_schema: Optional[str] = None,
    tenant_id: Optional[int] = None,
) -> None:
    """Dispatch webhook to provider handlers and emit events."""
    try:
        if provider == "stripe":
            evt_type = payload.get("type")
            # Minimal example mappings
            if evt_type == "invoice.payment_succeeded":
                emit_event(
                    "StripeInvoicePaid",
                    {
                        "tenant_schema": tenant_schema,
                        "tenant_id": tenant_id,
                        "stripe": payload,
                    },
                )
                return
            if evt_type == "customer.subscription.updated":
                emit_event(
                    "StripeSubscriptionUpdated",
                    {
                        "tenant_schema": tenant_schema,
                        "tenant_id": tenant_id,
                        "stripe": payload,
                    },
                )
                return
            # Default: record generic stripe event
            emit_event(
                "StripeEvent",
                {
                    "tenant_schema": tenant_schema,
                    "tenant_id": tenant_id,
                    "stripe": payload,
                },
            )
            return
        # Other providers can be added here
        emit_event(
            "WebhookReceived",
            {
                "tenant_schema": tenant_schema,
                "tenant_id": tenant_id,
                "provider": provider,
                "payload": payload,
            },
        )
    except Exception:
        # Let caller handle errors/ DLQ via event layer
        logger.exception("Failed to dispatch webhook", extra={"provider": provider})
