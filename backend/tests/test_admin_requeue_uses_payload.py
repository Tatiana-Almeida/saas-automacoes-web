import pytest
from django.test import override_settings


@pytest.mark.django_db
def test_admin_requeue_dlq_uses_stored_payload(client):
    from apps.auditing.admin import AuditLogAdmin
    from apps.auditing.models import AuditLog
    from django.contrib import admin as dj_admin

    # DLQ log where row has tenant_schema=acme but payload overrides to omega
    dlq = AuditLog.objects.create(
        user=None,
        path="/events/DLQ/PlanUpgraded",
        method="EVENT",
        source="events",
        action="event_DLQ",
        status_code=500,
        tenant_schema="acme",
        tenant_id=1,
        payload={"tenant_schema": "omega", "tenant_id": 2},
    )

    model_admin = AuditLogAdmin(AuditLog, dj_admin.site)

    class DummyReq:
        pass

    req = DummyReq()

    with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
        model_admin.requeue_selected_dlq(req, AuditLog.objects.filter(id=dlq.id))
        # Event listener should honor payload override (tenant_schema=omega)
        assert AuditLog.objects.filter(
            action="event_PlanUpgraded", tenant_schema="omega"
        ).exists()
