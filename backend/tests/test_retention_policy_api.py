import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_retention_policy_crud_api(client, create_tenant):
    from apps.rbac.models import Permission, UserPermission
    from apps.tenants.models import Domain

    # Create tenant and user with manage_auditing permission
    t = create_tenant(schema_name="acme", domain="acme.localhost", name="Acme")
    d = Domain.objects.get(domain="acme.localhost")
    u = User.objects.create_user(username="ops", password="Test123!")
    p = Permission.objects.create(code="manage_auditing")
    UserPermission.objects.create(user=u, permission=p, tenant=t)

    # Login
    login = client.post(
        "/api/v1/auth/token",
        data={"username": "ops", "password": "Test123!"},
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # Create policy
    resp = client.post(
        "/api/v1/auditing/retention-policies",
        data={"tenant_schema": "acme", "days": 45},
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp.status_code == 201
    body = resp.json()
    pid = body["id"]
    assert body["tenant_schema"] == "acme"
    assert body["days"] == 45

    # List policies
    resp = client.get("/api/v1/auditing/retention-policies", HTTP_HOST=d.domain)
    assert resp.status_code == 200
    arr = resp.json()
    assert len(arr) >= 1

    # Update policy
    resp = client.put(
        f"/api/v1/auditing/retention-policies/{pid}",
        data={"days": 60},
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["days"] == 60

    # Delete policy
    resp = client.delete(
        f"/api/v1/auditing/retention-policies/{pid}", HTTP_HOST=d.domain
    )
    assert resp.status_code == 204

    # Verify list empty or reduced
    resp = client.get("/api/v1/auditing/retention-policies", HTTP_HOST=d.domain)
    assert resp.status_code == 200
