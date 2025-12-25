import pytest
from django.test import override_settings


@pytest.mark.django_db
def test_quiet_bypass_actions_allow_multiple_sends(monkeypatch):
    from apps.auditing.models import AuditLog
    from apps.auditing import tasks as audit_tasks

    # Simulate successful webhook
    monkeypatch.setattr(audit_tasks, "_post_webhook", lambda url, payload: (200, "ok"))

    # Create two logs with same action but bypassed
    log1 = AuditLog.objects.create(
        path="/x",
        method="POST",
        source="view",
        action="security_incident",
        tenant_schema="acme",
        status_code=200,
    )
    log2 = AuditLog.objects.create(
        path="/y",
        method="POST",
        source="view",
        action="security_incident",
        tenant_schema="acme",
        status_code=200,
    )

    with override_settings(
        ALERT_WEBHOOK_ENABLED=True,
        ALERT_WEBHOOK_URL="http://example.com",
        ALERT_WEBHOOK_QUIET_MINUTES=60,
        ALERT_WEBHOOK_QUIET_BYPASS_ACTIONS=["security_incident"],
    ):
        r1 = audit_tasks.send_audit_alert(log1.id)
        assert r1.get("status") == "sent"
        r2 = audit_tasks.send_audit_alert(log2.id)
        assert r2.get("status") == "sent"
