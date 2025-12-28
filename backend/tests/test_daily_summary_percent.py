import json

import pytest
from apps.tenants.models import Domain
from django.contrib.auth import get_user_model
from django.test import override_settings

User = get_user_model()


@pytest.mark.django_db
@override_settings(
    TENANT_PLAN_DAILY_LIMITS={
        "free": {
            "send_whatsapp": 2,
        }
    }
)
def test_daily_summary_includes_percent_used(client, create_tenant):
    create_tenant(
        schema_name="percent", domain="percent.localhost", name="Percent", plan="free"
    )
    d = Domain.objects.get(domain="percent.localhost")

    User.objects.create_user(username="admin", password="Test123!", is_staff=True)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "admin", "password": "Test123!"}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # Use one action so used=1 of 2
    r = client.post(
        "/api/v1/whatsapp/messages/send",
        data=json.dumps({"to": "+15550009999", "message": "hello"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert 200 <= r.status_code < 300

    # Check summary
    resp = client.get("/api/v1/core/throttle/daily/summary", HTTP_HOST=d.domain)
    assert resp.status_code == 200
    payload = resp.json()
    daily = {item["category"]: item for item in payload.get("daily", [])}
    assert "send_whatsapp" in daily
    assert daily["send_whatsapp"]["percent_used_today"] == 50.0
