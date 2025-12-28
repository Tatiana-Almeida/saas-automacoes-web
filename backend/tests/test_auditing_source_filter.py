import json

import pytest
from apps.auditing.models import AuditLog
from apps.rbac.models import Permission, UserPermission
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_audit_list_filter_by_source(client):
    u = User.objects.create_user(username="audit_src", password="Test123!")

    # Grant view permission so the audit-list API is accessible
    perm, _ = Permission.objects.get_or_create(code="view_audit_logs")
    UserPermission.objects.create(user=u, permission=perm)

    # Login for cookie
    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "audit_src", "password": "Test123!"}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # Create audit entries with different sources
    AuditLog.objects.create(user=u, path="/admin/act", method="ADMIN", source="admin")
    AuditLog.objects.create(user=u, path="/cli/run", method="CLI", source="cli")

    # Filter by source=cli
    resp_cli = client.get("/api/v1/auditing/logs", {"source": "cli"})
    assert resp_cli.status_code == 200
    data_cli = resp_cli.json()
    assert any(item.get("source") == "cli" for item in data_cli.get("results", []))

    # Filter by source=admin
    resp_admin = client.get("/api/v1/auditing/logs", {"source": "admin"})
    assert resp_admin.status_code == 200
    data_admin = resp_admin.json()
    assert any(item.get("source") == "admin" for item in data_admin.get("results", []))
