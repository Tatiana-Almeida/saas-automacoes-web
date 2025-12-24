import pytest
from django.core.management import call_command
from django.utils import timezone

@pytest.mark.django_db
def test_purge_dlq_command_deletes_old_entries():
    from apps.auditing.models import AuditLog
    # Create two DLQ entries: one old and one recent
    old = AuditLog.objects.create(action='event_DLQ', method='EVENT', source='events', status_code=500, tenant_schema='acme', path='/events/DLQ/FailEvent')
    recent = AuditLog.objects.create(action='event_DLQ', method='EVENT', source='events', status_code=500, tenant_schema='acme', path='/events/DLQ/AnotherFail')

    # Backdate 'old' beyond 10 days
    AuditLog.objects.filter(id=old.id).update(created_at=timezone.now() - timezone.timedelta(days=20))

    # Run purge with 10 days threshold
    call_command('purge_dlq', '--days', '10')

    assert not AuditLog.objects.filter(id=old.id).exists()
    assert AuditLog.objects.filter(id=recent.id).exists()
