import pytest

@pytest.mark.django_db
def test_admin_csv_export_includes_payload(client):
    from django.contrib import admin as dj_admin
    from apps.auditing.models import AuditLog
    from apps.auditing.admin import AuditLogAdmin

    a = AuditLog.objects.create(path='/x', method='GET', source='events', action='event_DLQ', status_code=500, payload={'k':'v'})
    b = AuditLog.objects.create(path='/y', method='POST', source='middleware', action='request', status_code=200)

    model_admin = AuditLogAdmin(AuditLog, dj_admin.site)

    class DummyReq:
        META = {}
    req = DummyReq()

    resp = model_admin.export_selected_as_csv(req, AuditLog.objects.filter(id__in=[a.id, b.id]).order_by('id'))
    content = resp.content.decode('utf-8')

    # Header contains payload
    assert 'payload' in content.splitlines()[0]
    # First row (a) contains serialized payload
    lines = content.splitlines()
    assert '"{\"k\": \"v\"}"' in lines[1] or '{"k": "v"}' in lines[1]
    # Second row (b) has empty payload field (ends with comma or empty column)
    assert lines[2].endswith(',') or lines[2].split(',')[-1] == ''
