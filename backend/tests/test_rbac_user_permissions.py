import json
import pytest
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant, Domain
from apps.rbac.models import Role, Permission, UserPermission

User = get_user_model()


@pytest.mark.django_db
def test_assign_and_list_user_permission(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="gamma", domain="gamma.localhost", name="Gamma", plan="pro"
    )
    d = Domain.objects.get(domain="gamma.localhost")

    pw = gen_password()
    admin = User.objects.create_user(username="admin_perm", password=pw)
    target = User.objects.create_user(username="perm_target", password=pw)

    p_manage = Permission.objects.create(code="manage_users")
    p_view_users = Permission.objects.create(code="view_users")
    p_custom = Permission.objects.create(code="send_whatsapp")

    # grant admin manage_users and view_users in tenant
    UserPermission.objects.create(user=admin, permission=p_manage, tenant=t)
    UserPermission.objects.create(user=admin, permission=p_view_users, tenant=t)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "admin_perm", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # Assign custom permission to target
    a = client.post(
        f"/api/v1/rbac/users/{target.id}/permissions/assign",
        data=json.dumps({"permission": "send_whatsapp"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert a.status_code == 200
    assert a.json()["permission"] == "send_whatsapp"

    # List permissions for target
    l = client.get(f"/api/v1/rbac/users/{target.id}/permissions", HTTP_HOST=d.domain)
    assert l.status_code == 200
    perms = [p["permission"] for p in l.json()]
    assert "send_whatsapp" in perms


@pytest.mark.django_db
def test_revoke_user_permission(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="delta", domain="delta.localhost", name="Delta", plan="pro"
    )
    d = Domain.objects.get(domain="delta.localhost")

    pw = gen_password()
    admin = User.objects.create_user(username="admin_rev", password=pw)
    target = User.objects.create_user(username="rev_target", password=pw)

    p_manage = Permission.objects.create(code="manage_users")
    p_view_users = Permission.objects.create(code="view_users")
    p_custom = Permission.objects.create(code="send_email")

    UserPermission.objects.create(user=admin, permission=p_manage, tenant=t)
    UserPermission.objects.create(user=admin, permission=p_view_users, tenant=t)
    UserPermission.objects.create(user=target, permission=p_custom, tenant=t)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "admin_rev", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # Revoke
    r = client.post(
        f"/api/v1/rbac/users/{target.id}/permissions/revoke",
        data=json.dumps({"permission": "send_email"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r.status_code == 204

    # Verify removal
    l = client.get(f"/api/v1/rbac/users/{target.id}/permissions", HTTP_HOST=d.domain)
    assert l.status_code == 200
    perms = [p["permission"] for p in l.json()]
    assert "send_email" not in perms


@pytest.mark.django_db
def test_permission_assign_denied_without_manage_users(
    client, gen_password, create_tenant
):
    t = create_tenant(
        schema_name="echo", domain="echo.localhost", name="Echo", plan="pro"
    )
    d = Domain.objects.get(domain="echo.localhost")

    pw = gen_password()
    admin = User.objects.create_user(username="admin_no", password=pw)
    target = User.objects.create_user(username="perm_target2", password=pw)

    Permission.objects.create(code="manage_users")
    Permission.objects.create(code="send_sms")

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "admin_no", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    a = client.post(
        f"/api/v1/rbac/users/{target.id}/permissions/assign",
        data=json.dumps({"permission": "send_sms"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert a.status_code == 403
    assert a.json()["permission"] == "manage_users"
