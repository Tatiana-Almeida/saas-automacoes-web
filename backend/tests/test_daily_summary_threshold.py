import json
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.tenants.models import Tenant, Domain

User = get_user_model()


@pytest.mark.django_db
@override_settings(
    TENANT_PLAN_DAILY_LIMITS={"free": {"send_whatsapp": 5}},
    TENANT_PLAN_DAILY_WARN_THRESHOLD=50,
)
def test_near_limit_flag_and_threshold_in_summary(client, create_tenant):
    t = create_tenant(
        schema_name="thresh", domain="thresh.localhost", name="Thresh", plan="free"
    )
    d = Domain.objects.get(domain="thresh.localhost")

    u = User.objects.create_user(username="admin", password="Test123!", is_staff=True)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "admin", "password": "Test123!"}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # Use 3/5 = 60% (near_limit true with threshold 50)
    for i in range(3):
        r = client.post(
            "/api/v1/whatsapp/messages/send",
            data=json.dumps({"to": "+15550009999", "message": f"msg{i}"}),
            content_type="application/json",
            HTTP_HOST=d.domain,
        )
        assert 200 <= r.status_code < 300

    resp = client.get("/api/v1/core/throttle/daily/summary", HTTP_HOST=d.domain)
    assert resp.status_code == 200
    payload = resp.json()
    daily = {item["category"]: item for item in payload.get("daily", [])}
    assert daily["send_whatsapp"]["threshold_percent"] == 50
    assert daily["send_whatsapp"]["percent_used_today"] == 60.0
    assert daily["send_whatsapp"]["near_limit"] is True

    # Now verify below threshold (use 1/5 = 20%)
    # Reset via endpoint
    reset = client.post(
        "/api/v1/core/throttle/daily/reset",
        data=json.dumps({"categories": ["send_whatsapp"]}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert reset.status_code == 200

    r2 = client.post(
        "/api/v1/whatsapp/messages/send",
        data=json.dumps({"to": "+15550009999", "message": "again"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert 200 <= r2.status_code < 300

    resp2 = client.get("/api/v1/core/throttle/daily/summary", HTTP_HOST=d.domain)
    assert resp2.status_code == 200
    daily2 = {item["category"]: item for item in resp2.json().get("daily", [])}
    assert daily2["send_whatsapp"]["percent_used_today"] == 20.0
    assert daily2["send_whatsapp"]["near_limit"] is False
