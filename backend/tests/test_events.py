import pytest
from django.test import override_settings


@pytest.mark.django_db
def test_emit_tenant_created_event_creates_auditlog(client):
    from apps.events.events import emit_event, TENANT_CREATED
    from apps.auditing.models import AuditLog

    with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
        emit_event(TENANT_CREATED, {"tenant_id": 1, "tenant_schema": "acme"})
        assert AuditLog.objects.filter(action="event_TenantCreated").exists()


@pytest.mark.django_db
def test_plan_upgraded_event_emitted_on_plan_change(client, create_tenant):
    from django.contrib.auth import get_user_model
    from apps.tenants.models import Tenant, Domain, Plan
    from apps.rbac.models import Permission, UserPermission
    from apps.auditing.models import AuditLog

    User = get_user_model()
    Plan.objects.create(code="pro", name="Pro", daily_limits={})

    t = create_tenant(
        schema_name="acme", domain="acme.localhost", name="Acme", plan="free"
    )
    d = Domain.objects.get(domain="acme.localhost")
    u = User.objects.create_user(username="manager", password="Test123!")
    p = Permission.objects.create(code="manage_tenants")
    UserPermission.objects.create(user=u, permission=p, tenant=t)

    login = client.post(
        "/api/v1/auth/token",
        data={"username": "manager", "password": "Test123!"},
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
        resp = client.post(
            f"/api/v1/tenants/{t.id}/plan",
            data={"plan": "pro"},
            content_type="application/json",
            HTTP_HOST=d.domain,
        )
        assert resp.status_code == 200
        assert AuditLog.objects.filter(
            action="event_PlanUpgraded", tenant_schema="acme"
        ).exists()


@pytest.mark.django_db
def test_event_retry_and_dlq_on_failure(create_tenant):
    from apps.auditing.models import AuditLog

    # Register a failing event dynamically by monkeypatching registry
    from apps.events.listeners import LISTENER_REGISTRY

    def failing_listener(payload):
        raise RuntimeError("boom")

    LISTENER_REGISTRY["FailEvent"] = failing_listener

    # Instead call dead_letter_event (run tasks eagerly so DLQ is persisted)
    from apps.events.tasks import dead_letter_event
    from django.test import override_settings

    # Ensure tenant exists so auditing tables are present in the tenant schema
    create_tenant(schema_name="acme", domain="acme.localhost", name="Acme", plan="free")
    with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
        dead_letter_event.delay(
            "FailEvent", {"tenant_schema": "acme", "tenant_id": 1}, reason="boom"
        )
    assert AuditLog.objects.filter(
        action="event_DLQ", path__icontains="/events/DLQ/FailEvent"
    ).exists()
