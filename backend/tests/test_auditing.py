import json

import pytest
from apps.auditing.models import AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_authenticated_request_creates_audit_log_entry(
    client, gen_password, create_tenant
):
    # ensure tenant schema exists and domain registered
    create_tenant(
        schema_name="audit", domain="audit.localhost", name="AuditTenant", plan="free"
    )
    client.defaults["HTTP_HOST"] = "audit.localhost"
    username = "audituser"
    password = gen_password()
    User.objects.create_user(username=username, password=password)

    # Ensure no logs yet
    AuditLog.objects.all().delete()

    # Login for cookie
    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # Perform an authenticated request that should be logged by middleware
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 200

    # Verify an audit log entry exists
    assert AuditLog.objects.count() >= 1
    entry = AuditLog.objects.latest("created_at")
    assert entry.user is not None
    assert entry.path
    assert entry.method in ("GET", "POST", "PUT", "PATCH", "DELETE")
