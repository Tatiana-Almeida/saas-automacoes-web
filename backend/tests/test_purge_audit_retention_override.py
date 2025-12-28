from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone


@pytest.mark.django_db
def test_purge_respects_per_tenant_retention_overrides(capsys):
    from apps.auditing.models import AuditLog
    from django.core.management import call_command

    now = timezone.now()

    # acme override = 30 days
    old_acme = now - timedelta(days=31)
    keep_acme = now - timedelta(days=20)
    # other default = 90 days
    old_other = now - timedelta(days=91)
    keep_other = now - timedelta(days=10)

    AuditLog.objects.create(
        path="/old1",
        method="GET",
        source="view",
        action="rbac_change",
        tenant_schema="acme",
        status_code=200,
        created_at=old_acme,
    )
    AuditLog.objects.create(
        path="/keep1",
        method="GET",
        source="view",
        action="rbac_change",
        tenant_schema="acme",
        status_code=200,
        created_at=keep_acme,
    )
    AuditLog.objects.create(
        path="/old2",
        method="GET",
        source="view",
        action="rbac_change",
        tenant_schema="beta",
        status_code=200,
        created_at=old_other,
    )
    AuditLog.objects.create(
        path="/keep2",
        method="GET",
        source="view",
        action="rbac_change",
        tenant_schema="beta",
        status_code=200,
        created_at=keep_other,
    )

    with override_settings(
        AUDIT_RETENTION_DEFAULT_DAYS=90, AUDIT_RETENTION_TENANT_DAYS={"acme": 30}
    ):
        call_command("purge_audit_logs")

    # Verify remaining
    remaining = AuditLog.objects.all()
    paths = sorted([a.path for a in remaining])
    assert paths == ["/keep1", "/keep2"]
