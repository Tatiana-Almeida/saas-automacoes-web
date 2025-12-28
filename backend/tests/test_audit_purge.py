from datetime import timedelta

import pytest
from apps.auditing.models import AuditLog
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

User = get_user_model()


@pytest.mark.django_db
def test_purge_audit_logs_removes_old_entries(gen_password):
    u = User.objects.create_user(username="oldlogger", password=gen_password())

    # Create two logs: one old, one recent
    old_log = AuditLog.objects.create(
        user=u,
        path="/x",
        method="GET",
        source="test",
        action="request",
        status_code=200,
    )
    recent_log = AuditLog.objects.create(
        user=u,
        path="/y",
        method="GET",
        source="test",
        action="request",
        status_code=200,
    )

    # Backdate the old log beyond retention window
    AuditLog.objects.filter(id=old_log.id).update(
        created_at=timezone.now() - timedelta(days=365)
    )

    # Sanity check: two logs exist
    assert AuditLog.objects.count() == 2

    # Purge older than 90 days (default)
    call_command("purge_audit_logs")

    # Only recent log should remain
    remaining = list(AuditLog.objects.values_list("id", flat=True))
    assert recent_log.id in remaining
    assert old_log.id not in remaining
