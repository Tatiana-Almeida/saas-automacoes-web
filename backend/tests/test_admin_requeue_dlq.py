import pytest
from django.test import override_settings


@pytest.mark.django_db
def test_admin_requeue_dlq_emits_event(client):
    from apps.auditing.admin import AuditLogAdmin
    from apps.auditing.models import AuditLog
    from django.contrib import admin as dj_admin

    # Create DLQ log for PlanUpgraded
    dlq = AuditLog.objects.create(
        user=None,
        path="/events/DLQ/PlanUpgraded",
        method="EVENT",
        source="events",
        action="event_DLQ",
        status_code=500,
        tenant_schema="acme",
        tenant_id=1,
    )

    # Prepare admin and fake queryset
    model_admin = AuditLogAdmin(AuditLog, dj_admin.site)

    class DummyReq:
        pass

    req = DummyReq()

    with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
        resp = model_admin.requeue_selected_dlq(req, AuditLog.objects.filter(id=dlq.id))
        assert "Requeued 1" in resp.content.decode()
        # Listener should have produced an audit entry for PlanUpgraded
        assert AuditLog.objects.filter(
            action="event_PlanUpgraded", tenant_schema="acme"
        ).exists()
