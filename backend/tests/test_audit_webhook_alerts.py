import pytest
from apps.auditing import tasks as audit_tasks
from apps.auditing.models import AuditLog
from django.contrib.auth import get_user_model
from django.test import override_settings

User = get_user_model()


@pytest.mark.django_db
def test_send_audit_alert_disabled_returns_disabled(gen_password):
    u = User.objects.create_user(username="alerter", password=gen_password())
    log = AuditLog.objects.create(
        user=u,
        path="/x",
        method="POST",
        source="test",
        action="rbac_change",
        status_code=200,
        tenant_schema="acme",
    )
    with override_settings(
        ALERT_WEBHOOK_ENABLED=False, ALERT_WEBHOOK_URL="http://localhost/hook"
    ):
        res = audit_tasks.send_audit_alert(log.id)
        assert res.get("status") == "disabled"


@pytest.mark.django_db
def test_send_audit_alert_success(monkeypatch, gen_password):
    u = User.objects.create_user(username="alerter2", password=gen_password())
    log = AuditLog.objects.create(
        user=u,
        path="/y",
        method="POST",
        source="test",
        action="rbac_change",
        status_code=200,
        tenant_schema="beta",
    )

    def fake_post(url, payload, headers=None):
        assert "rbac_change" in payload.get("text", "")
        return 200, "ok"

    monkeypatch.setattr(audit_tasks, "_post_webhook", fake_post)

    with override_settings(
        ALERT_WEBHOOK_ENABLED=True,
        ALERT_WEBHOOK_URL="http://localhost/hook",
        AUDIT_CRITICAL_ACTIONS=["rbac_change"],
    ):
        res = audit_tasks.send_audit_alert(log.id)
        assert res.get("status") == "sent"


@pytest.mark.django_db
def test_post_save_signal_triggers_for_critical_action(monkeypatch):
    calls = {"n": 0}

    def fake_delay(log_id):
        calls["n"] += 1

    monkeypatch.setattr(audit_tasks.send_audit_alert, "delay", staticmethod(fake_delay))

    with override_settings(
        ALERT_WEBHOOK_ENABLED=True, AUDIT_CRITICAL_ACTIONS=["rbac_change"]
    ):
        # Creating this log should trigger the signal which enqueues the task
        AuditLog.objects.create(
            user=None,
            path="/z",
            method="POST",
            source="test",
            action="rbac_change",
            status_code=200,
            tenant_schema="gamma",
        )
        assert calls["n"] == 1
