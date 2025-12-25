import pytest
from django.test import override_settings
from django.utils import timezone
from datetime import timedelta


@pytest.mark.django_db
def test_purge_uses_admin_retention_policy(capsys):
    from apps.auditing.models import AuditLog, AuditRetentionPolicy
    from django.core.management import call_command

    now = timezone.now()

    # Admin-defined policy: acme -> 30 days
    AuditRetentionPolicy.objects.create(tenant_schema="acme", days=30)

    # Create logs
    AuditLog.objects.create(
        path="/old1",
        method="GET",
        source="view",
        action="rbac_change",
        tenant_schema="acme",
        status_code=200,
        created_at=now - timedelta(days=31),
    )
    AuditLog.objects.create(
        path="/keep1",
        method="GET",
        source="view",
        action="rbac_change",
        tenant_schema="acme",
        status_code=200,
        created_at=now - timedelta(days=20),
    )

    AuditLog.objects.create(
        path="/old2",
        method="GET",
        source="view",
        action="rbac_change",
        tenant_schema="beta",
        status_code=200,
        created_at=now - timedelta(days=95),
    )
    AuditLog.objects.create(
        path="/keep2",
        method="GET",
        source="view",
        action="rbac_change",
        tenant_schema="beta",
        status_code=200,
        created_at=now - timedelta(days=10),
    )

    # Default via settings: 90 days
    with override_settings(
        AUDIT_RETENTION_DEFAULT_DAYS=90, AUDIT_RETENTION_TENANT_DAYS={}
    ):
        call_command("purge_audit_logs")

    remaining = AuditLog.objects.all()
    assert sorted([a.path for a in remaining]) == ["/keep1", "/keep2"]
