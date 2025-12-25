import json
import pytest
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant, Domain, Plan
from apps.auditing.models import AuditLog
from apps.auditing import tasks as audit_tasks

User = get_user_model()


@pytest.mark.django_db
def test_tenant_plan_change_updates_fields_and_logs(monkeypatch, client, create_tenant):
    # Seed plans
    Plan.objects.create(code="free", name="Free", daily_limits={})
    Plan.objects.create(code="pro", name="Pro", daily_limits={})

    # Create tenant and domain (use helper to ensure migrations)
    t = create_tenant(
        schema_name="acme", domain="acme.localhost", name="ACME", plan="free"
    )

    # Admin user with manage_tenants permission
    admin = User.objects.create_user(username="admin_plan", password="Test123!")
    # Simplify: grant via direct UserPermission creation would require import
    from apps.rbac.models import Permission, UserPermission

    p = Permission.objects.create(code="manage_tenants")
    UserPermission.objects.create(user=admin, permission=p, tenant=t)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "admin_plan", "password": "Test123!"}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    calls = {"n": 0}
    monkeypatch.setattr(
        audit_tasks.send_audit_alert,
        "delay",
        staticmethod(lambda *_args, **_kw: calls.__setitem__("n", calls["n"] + 1)),
    )

    from django.test import override_settings

    with override_settings(
        ALERT_WEBHOOK_ENABLED=True, AUDIT_CRITICAL_ACTIONS=["plan_change"]
    ):
        resp = client.post(
            f"/api/v1/tenants/{t.id}/plan",
            data=json.dumps({"plan": "pro"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["plan"] == "pro"
        # Reload tenant
        t.refresh_from_db()
        assert t.plan == "pro"
        assert t.plan_ref and t.plan_ref.code == "pro"
        # AuditLog present and alert enqueued
        assert AuditLog.objects.filter(
            action="plan_change", tenant_schema="acme"
        ).exists()
        assert calls["n"] == 1
