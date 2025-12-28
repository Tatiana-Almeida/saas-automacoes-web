from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def compute_daily_near_limits(schema: str, daily_cfg: dict, warn_threshold: int):
    """Compute categories nearing daily limit for a tenant schema.

    Returns a list of dicts: {category, used, limit, percent_used}
    """
    results = []
    today = timezone.now().date().isoformat()
    for category, limit in (daily_cfg or {}).items():
        key = f"plan_limit:{schema}:{category}:{today}"
        used = int(cache.get(key, 0))
        percent = None
        if isinstance(limit, int) and limit > 0:
            try:
                percent = round((used / int(limit)) * 100, 2)
            except Exception:
                percent = None
        is_near = False
        try:
            if isinstance(percent, (int, float)) and isinstance(warn_threshold, int):
                is_near = percent >= warn_threshold
        except Exception:
            is_near = False
        if is_near:
            results.append(
                {
                    "category": category,
                    "used": used,
                    "limit": limit,
                    "percent_used": percent,
                }
            )
    return results


def _tenant_plan_limits(tenant):
    """Resolve plan code and daily limits for a tenant, preferring model-based limits."""
    plan_obj = getattr(tenant, "plan_ref", None)
    plan_code = getattr(plan_obj, "code", None) or getattr(tenant, "plan", "free")
    # Prefer model-based limits
    daily_cfg = None
    try:
        dl = getattr(plan_obj, "daily_limits", None)
        if isinstance(dl, dict):
            daily_cfg = dl
    except Exception:
        daily_cfg = None
    if daily_cfg is None:
        daily_cfg = getattr(settings, "TENANT_PLAN_DAILY_LIMITS", {}).get(plan_code, {})
    return plan_code, daily_cfg


def _dispatch_alert(tenant, alert: dict):
    """Create an audit entry and optionally send an email alert."""
    try:
        from apps.auditing.models import AuditLog

        AuditLog.objects.create(
            user=None,
            path=f"/alerts/daily_limit_near/{alert.get('category')}",
            method="SYSTEM",
            source="alert",
            ip_address=None,
        )
    except Exception:
        # Swallow audit failures to avoid breaking alerting loop
        pass

    # Optional email alert to a configured inbox
    try:
        to_email = getattr(settings, "TENANT_ALERTS_EMAIL_TO", None)
        if to_email:
            from apps.mailer.tasks import send_email_message

            tenant_name = getattr(tenant, "name", None) or getattr(
                tenant, "schema_name", "unknown"
            )
            subject = (
                f"[SaaS] Uso diário perto do limite: {alert.get('category')} "
                f"({tenant_name})"
            )
            body = (
                f"Tenant: {tenant_name}\n"
                f"Categoria: {alert.get('category')}\n"
                f"Usado hoje: {alert.get('used')} de {alert.get('limit')} "
                f"({alert.get('percent_used')}%)\n"
            )
            # fire-and-forget via Celery
            send_email_message.delay(to_email, subject, body)
    except Exception:
        pass


def check_tenant_daily_limit_warns(tenant):
    """Check a single tenant and dispatch alerts for near-limit categories."""
    schema = getattr(tenant, "schema_name", "public")
    _, daily_cfg = _tenant_plan_limits(tenant)
    warn_threshold = getattr(settings, "TENANT_PLAN_DAILY_WARN_THRESHOLD", 80)
    alerts = compute_daily_near_limits(schema, daily_cfg, warn_threshold)
    for alert in alerts:
        _dispatch_alert(tenant, alert)
    return alerts


@shared_task
def check_daily_limit_warns():
    """Periodic task: iterate active tenants and emit near-limit alerts."""
    try:
        from apps.tenants.models import Tenant

        tenants = Tenant.objects.filter(is_active=True)
        total_alerts = 0
        for tenant in tenants:
            alerts = check_tenant_daily_limit_warns(tenant)
            total_alerts += len(alerts)
        return {"tenants": tenants.count(), "alerts": total_alerts}
    except Exception as exc:
        # Return exception string for visibility in Celery results
        return {"error": str(exc)}
