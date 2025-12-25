import pytest


@pytest.mark.django_db
def test_admin_has_payload_column_renders_marker(client):
    from django.contrib import admin as dj_admin
    from apps.auditing.models import AuditLog
    from apps.auditing.admin import AuditLogAdmin

    with_payload = AuditLog.objects.create(
        path="/",
        method="GET",
        source="events",
        action="event_DLQ",
        status_code=500,
        payload={"a": 1},
    )
    without_payload = AuditLog.objects.create(
        path="/", method="GET", source="events", action="event_DLQ", status_code=500
    )

    model_admin = AuditLogAdmin(AuditLog, dj_admin.site)

    assert model_admin.has_payload(with_payload) == "✔"
    assert model_admin.has_payload(without_payload) == "—"
