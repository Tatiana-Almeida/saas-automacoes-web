import pytest
from django.core.cache import cache
from django.test import override_settings


@pytest.mark.django_db
def test_alert_quiet_period_suppresses_second_send(monkeypatch):
    from apps.auditing import tasks as audit_tasks
    from apps.auditing.models import AuditLog

    # Simulate successful webhook
    monkeypatch.setattr(audit_tasks, "_post_webhook", lambda url, payload: (200, "ok"))

    # Create two logs with same tenant/action
    log1 = AuditLog.objects.create(
        path="/x",
        method="POST",
        source="view",
        action="plan_change",
        tenant_schema="acme",
        status_code=200,
    )
    log2 = AuditLog.objects.create(
        path="/y",
        method="POST",
        source="view",
        action="plan_change",
        tenant_schema="acme",
        status_code=200,
    )

    cache.delete(f"audit_alert:quiet:{log1.tenant_schema}:{log1.action}")

    with override_settings(
        ALERT_WEBHOOK_ENABLED=True,
        ALERT_WEBHOOK_URL="http://example.com",
        ALERT_WEBHOOK_QUIET_MINUTES=60,
    ):
        r1 = audit_tasks.send_audit_alert(log1.id)
        assert r1.get("status") == "sent"
        r2 = audit_tasks.send_audit_alert(log2.id)
        assert r2.get("status") == "suppressed"


@pytest.mark.django_db
def test_alert_quiet_period_different_action_not_suppressed(monkeypatch):
    from apps.auditing import tasks as audit_tasks
    from apps.auditing.models import AuditLog

    monkeypatch.setattr(audit_tasks, "_post_webhook", lambda url, payload: (200, "ok"))

    log1 = AuditLog.objects.create(
        path="/x",
        method="POST",
        source="view",
        action="rbac_change",
        tenant_schema="acme",
        status_code=200,
    )
    log2 = AuditLog.objects.create(
        path="/y",
        method="POST",
        source="view",
        action="plan_change",
        tenant_schema="acme",
        status_code=200,
    )

    cache.delete(f"audit_alert:quiet:{log1.tenant_schema}:{log1.action}")

    with override_settings(
        ALERT_WEBHOOK_ENABLED=True,
        ALERT_WEBHOOK_URL="http://example.com",
        ALERT_WEBHOOK_QUIET_MINUTES=60,
    ):
        r1 = audit_tasks.send_audit_alert(log1.id)
        assert r1.get("status") == "sent"
        r2 = audit_tasks.send_audit_alert(log2.id)
        assert r2.get("status") == "sent"
