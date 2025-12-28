import pytest
from apps.tenants.models import Domain, Plan
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_tenant_plan_detail_prefers_model_daily_limits(client, create_tenant):
    # Seed plans with model daily limits
    Plan.objects.create(code="pro", name="Pro", daily_limits={"send_whatsapp": 999})

    # Create tenant linked to pro plan
    t = create_tenant(
        schema_name="delta", domain="delta.localhost", name="Delta", plan="free"
    )
    d = Domain.objects.get(domain="delta.localhost")
    from apps.rbac.models import Permission, UserPermission

    u = User.objects.create_user(username="viewer", password="Test123!")
    p = Permission.objects.create(code="manage_tenants")
    UserPermission.objects.create(user=u, permission=p, tenant=t)

    # Link plan_ref
    from apps.tenants.models import Plan as PlanModel

    t.plan_ref = PlanModel.objects.get(code="pro")
    t.plan = "pro"
    t.save(update_fields=["plan", "plan_ref"])

    # Login
    login = client.post(
        "/api/v1/auth/token",
        data={"username": "viewer", "password": "Test123!"},
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    resp = client.get(f"/api/v1/tenants/{t.id}/plan", HTTP_HOST=d.domain)
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == "pro"
    assert body["plan_ref"] == "pro"
    assert body["daily_limits"].get("send_whatsapp") == 999
