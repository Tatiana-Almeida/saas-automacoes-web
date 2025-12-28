import json

import pytest
from apps.tenants.models import Domain
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_daily_summary_endpoint(client, gen_password, create_tenant):
    create_tenant(schema_name="acme", domain="acme.localhost", name="ACME", plan="free")
    d = Domain.objects.get(domain="acme.localhost")

    pw = gen_password()
    User.objects.create_user(username="admin_sum", password=pw, is_staff=True)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "admin_sum", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    resp = client.get("/api/v1/core/throttle/daily/summary", HTTP_HOST=d.domain)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("schema") == "acme"
    assert "daily" in payload
    assert isinstance(payload["daily"], list)
