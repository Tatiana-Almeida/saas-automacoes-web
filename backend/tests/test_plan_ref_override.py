import json

import pytest
from apps.rbac.models import Permission, UserPermission
from apps.tenants.models import Domain, Plan
from django.contrib.auth import get_user_model
from django.test import override_settings

User = get_user_model()


@pytest.mark.django_db
@override_settings(
    TENANT_PLAN_DAILY_LIMITS={
        "free": {
            "send_whatsapp": 5,  # global would allow 5
        }
    }
)
def test_plan_ref_daily_limits_override_settings(client, create_tenant):
    # Create a custom plan with stricter limit
    plan = Plan.objects.create(
        code="vip", name="VIP", daily_limits={"send_whatsapp": 1}
    )

    # Tenant has string plan 'free' but FK plan_ref points to 'vip'
    t = create_tenant(
        schema_name="acme",
        domain="acme.localhost",
        name="ACME",
        plan="free",
        plan_ref=plan,
    )
    d = Domain.objects.get(domain="acme.localhost")

    # User with permission in this tenant
    u = User.objects.create_user(
        username="ovr_user", password="Test123!", is_staff=True
    )
    p_send = Permission.objects.create(code="send_whatsapp")
    UserPermission.objects.create(user=u, permission=p_send, tenant=t)

    # Login
    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "ovr_user", "password": "Test123!"}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # First send allowed (model limit=1)
    resp1 = client.post(
        "/api/v1/whatsapp/messages/send",
        data=json.dumps({"to": "+5511999999999", "message": "Olá"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert 200 <= resp1.status_code < 300

    # Second send should be blocked despite settings allowing 5
    resp2 = client.post(
        "/api/v1/whatsapp/messages/send",
        data=json.dumps({"to": "+5511999999999", "message": "Excesso"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp2.status_code == 429
    data = resp2.json()
    assert data.get("category") == "send_whatsapp"
    # plan code should reflect plan_ref preference ('vip')
    assert data.get("plan") == "vip"
