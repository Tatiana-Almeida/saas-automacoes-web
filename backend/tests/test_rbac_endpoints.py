import json

import pytest
from apps.rbac.models import Permission, Role, UserPermission, UserRole
from apps.tenants.models import Domain
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_assign_role_requires_manage_users_permission(
    client, gen_password, create_tenant
):
    # Setup tenant and domain (use helper to apply tenant migrations)
    t = create_tenant(
        schema_name="acme", domain="acme.localhost", name="ACME", plan="pro"
    )
    d = Domain.objects.get(domain="acme.localhost")

    # Create users
    pw = gen_password()
    admin = User.objects.create_user(username="admin1", password=pw)
    target = User.objects.create_user(username="target1", password=pw)

    # Seed role and permission
    Role.objects.create(name="Viewer")
    perm = Permission.objects.create(code="manage_users")
    UserPermission.objects.create(user=admin, permission=perm, tenant=t)

    # Login admin
    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "admin1", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # Assign Viewer role to target in current tenant
    resp = client.post(
        f"/api/v1/rbac/users/{target.id}/roles/assign",
        data=json.dumps({"role": "Viewer"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("role") == "Viewer"


@pytest.mark.django_db
def test_assign_role_denied_without_permission(client, gen_password, create_tenant):
    create_tenant(schema_name="beta", domain="beta.localhost", name="Beta", plan="free")
    d = Domain.objects.get(domain="beta.localhost")

    pw = gen_password()
    User.objects.create_user(username="admin2", password=pw)
    target = User.objects.create_user(username="target2", password=pw)

    Role.objects.create(name="Viewer")
    Permission.objects.create(code="manage_users")

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "admin2", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    resp = client.post(
        f"/api/v1/rbac/users/{target.id}/roles/assign",
        data=json.dumps({"role": "Viewer"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data.get("permission") == "manage_users"


@pytest.mark.django_db
def test_list_roles_scoped_by_tenant(client, gen_password, create_tenant):
    # Two tenants
    ta = create_tenant(
        schema_name="alpha", domain="alpha.localhost", name="Alpha", plan="pro"
    )
    da = Domain.objects.get(domain="alpha.localhost")
    tb = create_tenant(
        schema_name="bravo", domain="bravo.localhost", name="Bravo", plan="pro"
    )
    db = Domain.objects.get(domain="bravo.localhost")

    pw = gen_password()
    admin = User.objects.create_user(username="admin3", password=pw)
    target = User.objects.create_user(username="target3", password=pw)

    role = Role.objects.create(name="Viewer")
    p_view = Permission.objects.create(code="view_users")

    # Grant view_users in both tenants
    UserPermission.objects.create(user=admin, permission=p_view, tenant=ta)
    UserPermission.objects.create(user=admin, permission=p_view, tenant=tb)

    # Assign role in tenant Alpha only
    UserRole.objects.create(user=target, role=role, tenant=ta)

    # Login admin
    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "admin3", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # List in Alpha: should include Viewer
    la = client.get(f"/api/v1/rbac/users/{target.id}/roles", HTTP_HOST=da.domain)
    assert la.status_code == 200
    roles_a = [r["role"] for r in la.json()]
    assert "Viewer" in roles_a

    # List in Bravo: should NOT include Viewer (scoped to Alpha)
    lb = client.get(f"/api/v1/rbac/users/{target.id}/roles", HTTP_HOST=db.domain)
    assert lb.status_code == 200
    roles_b = [r["role"] for r in lb.json()]
    assert "Viewer" not in roles_b
