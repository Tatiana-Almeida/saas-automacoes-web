import json

import pytest
from apps.rbac.models import Permission, Role, UserPermission, UserRole
from apps.tenants.models import Domain
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_bulk_rbac_apply_success(client, create_tenant):
    t = create_tenant(
        schema_name="omega", domain="omega.localhost", name="Omega", plan="pro"
    )
    d = Domain.objects.get(domain="omega.localhost")

    admin = User.objects.create_user(username="bulk_admin", password="Test123!")
    u1 = User.objects.create_user(username="bulk_u1", password="Test123!")
    u2 = User.objects.create_user(username="bulk_u2", password="Test123!")

    # Seed roles and permissions
    Role.objects.create(name="Viewer")
    Role.objects.create(name="Operator")
    p_manage = Permission.objects.create(code="manage_users")
    Permission.objects.create(code="send_sms")

    # Grant admin manage_users in tenant
    UserPermission.objects.create(user=admin, permission=p_manage, tenant=t)

    # Login admin
    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "bulk_admin", "password": "Test123!"}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    payload = {
        "assign": {
            "roles": [
                {"username": "bulk_u1", "role": "Viewer"},
                {"username": "bulk_u2", "role": "Operator"},
            ],
            "permissions": [
                {"username": "bulk_u1", "permission": "send_sms"},
            ],
        },
        "revoke": {
            "roles": [{"username": "bulk_u2", "role": "Viewer"}],
            "permissions": [],
        },
    }

    resp = client.post(
        "/api/v1/rbac/bulk/apply",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("applied") is True
    assert data.get("errors") == []

    # Verify assignments in tenant
    assert UserRole.objects.filter(user=u1, role__name="Viewer", tenant=t).exists()
    assert UserRole.objects.filter(user=u2, role__name="Operator", tenant=t).exists()
    assert UserPermission.objects.filter(
        user=u1, permission__code="send_sms", tenant=t
    ).exists()


@pytest.mark.django_db
def test_bulk_rbac_apply_partial_errors(client, create_tenant):
    t = create_tenant(
        schema_name="sigma", domain="sigma.localhost", name="Sigma", plan="pro"
    )
    d = Domain.objects.get(domain="sigma.localhost")

    admin = User.objects.create_user(username="bulk_admin2", password="Test123!")
    User.objects.create_user(username="bulk_err_u1", password="Test123!")

    Role.objects.create(name="Viewer")
    p_manage = Permission.objects.create(code="manage_users")

    UserPermission.objects.create(user=admin, permission=p_manage, tenant=t)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "bulk_admin2", "password": "Test123!"}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    payload = {
        "assign": {
            "roles": [
                {"username": "bulk_err_u1", "role": "Viewer"},
                {"username": "unknown_user", "role": "Viewer"},
            ],
            "permissions": [
                {"username": "bulk_err_u1", "permission": "nonexistent_perm"}
            ],
        },
        "revoke": {
            "roles": [{"username": "bulk_err_u1", "role": "NonexistentRole"}],
            "permissions": [],
        },
    }

    resp = client.post(
        "/api/v1/rbac/bulk/apply",
        data=json.dumps(payload),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp.status_code == 207
    data = resp.json()
    assert data.get("applied") is True
    assert isinstance(data.get("errors"), list)
    assert len(data.get("errors")) >= 1
