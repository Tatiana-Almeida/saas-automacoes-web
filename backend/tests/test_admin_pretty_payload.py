import pytest


@pytest.mark.django_db
def test_admin_pretty_payload_renders_json(client):
    from apps.auditing.admin import AuditLogAdmin
    from apps.auditing.models import AuditLog
    from django.contrib import admin as dj_admin

    obj = AuditLog.objects.create(
        path="/",
        method="GET",
        source="events",
        action="event_DLQ",
        status_code=500,
        payload={"foo": "bar", "n": 1},
    )

    model_admin = AuditLogAdmin(AuditLog, dj_admin.site)
    html = model_admin.pretty_payload(obj)
    assert "foo" in str(html)
    assert "bar" in str(html)
    assert "<pre" in str(html)
