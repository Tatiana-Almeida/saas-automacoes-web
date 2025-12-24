from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from .models import AuditLog
from .utils import get_client_ip
from django.conf import settings
from .tasks import send_audit_alert


def _tenant_info_from_request(request):
    try:
        tenant = getattr(request, 'tenant', None)
        return getattr(tenant, 'schema_name', None), getattr(tenant, 'id', None)
    except Exception:
        return None, None


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    try:
        schema, tenant_id = _tenant_info_from_request(request)
        AuditLog.objects.create(
            user=user,
            path=getattr(request, 'path', '/auth/signal') or '/auth/signal',
            method=(getattr(request, 'method', None) or 'POST'),
            source='signal',
            action='login',
            status_code=200,
            tenant_schema=schema,
            tenant_id=tenant_id,
            ip_address=get_client_ip(request),
        )
    except Exception:
        pass


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    try:
        schema, tenant_id = _tenant_info_from_request(request)
        AuditLog.objects.create(
            user=user,
            path=getattr(request, 'path', '/auth/signal') or '/auth/signal',
            method=(getattr(request, 'method', None) or 'POST'),
            source='signal',
            action='logout',
            status_code=200,
            tenant_schema=schema,
            tenant_id=tenant_id,
            ip_address=get_client_ip(request),
        )
    except Exception:
        pass


@receiver(user_login_failed)
def on_user_login_failed(sender, credentials, request, **kwargs):
    try:
        schema, tenant_id = _tenant_info_from_request(request)
        AuditLog.objects.create(
            user=None,
            path=getattr(request, 'path', '/auth/signal') or '/auth/signal',
            method=(getattr(request, 'method', None) or 'POST'),
            source='signal',
            action='login_failed',
            status_code=401,
            tenant_schema=schema,
            tenant_id=tenant_id,
            ip_address=get_client_ip(request),
        )
    except Exception:
        pass


@receiver(post_save, sender=AuditLog)
def on_auditlog_created(sender, instance: AuditLog, created, **kwargs):
    if not created:
        return
    try:
        enabled = getattr(settings, 'ALERT_WEBHOOK_ENABLED', False)
        if not enabled:
            return
        actions = set(getattr(settings, 'AUDIT_CRITICAL_ACTIONS', []) or [])
        if getattr(instance, 'action', None) in actions:
            # fire-and-forget
            send_audit_alert.delay(instance.id)
    except Exception:
        # Never block on alert errors
        pass
