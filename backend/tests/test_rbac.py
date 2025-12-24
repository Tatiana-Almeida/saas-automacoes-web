import json
import pytest
from django.contrib.auth import get_user_model

from apps.rbac.models import Role, Permission, UserRole

User = get_user_model()


@pytest.mark.django_db
def test_auditing_access_allowed_for_viewer_with_permission(client, gen_password):
    # Seed permission and role
    p_view = Permission.objects.create(code='view_audit_logs')
    role_viewer = Role.objects.create(name='Viewer')
    role_viewer.permissions.add(p_view)

    # Create user and assign role
    pw = gen_password()
    u = User.objects.create_user(username='viewer', password=pw)
    UserRole.objects.create(user=u, role=role_viewer)

    # Login to get cookie
    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "viewer", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # Access auditing list (requires 'view_audit_logs')
    resp = client.get("/api/v1/auditing/logs")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_auditing_access_denied_without_permission(client, gen_password):
    pw = gen_password()
    u = User.objects.create_user(username='noperm', password=pw)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "noperm", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    resp = client.get("/api/v1/auditing/logs")
    assert resp.status_code == 403
    data = resp.json()
    assert data.get("permission") == "view_audit_logs"
