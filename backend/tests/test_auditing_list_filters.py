import json
import pytest
from django.contrib.auth import get_user_model
from apps.rbac.models import Permission, UserPermission

User = get_user_model()


@pytest.mark.django_db
def test_auditing_list_filters_and_ordering(client, gen_password):
    username = "auditlistuser"
    password = gen_password()
    user = User.objects.create_user(username=username, password=password)

    # Login for cookie
    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # Generate audit logs via authenticated requests
    r1 = client.get("/api/v1/users/me")
    assert r1.status_code == 200
    r2 = client.get("/api/v1/users/me?x=2")
    assert r2.status_code == 200

    # Grant view permission so the audit-list API is accessible
    perm, _ = Permission.objects.get_or_create(code="view_audit_logs")
    UserPermission.objects.create(user=user, permission=perm)

    # List logs with path filter
    list1 = client.get("/api/v1/auditing/logs", {"path_contains": "/api/v1/users/me"})
    assert list1.status_code == 200
    data1 = list1.json()
    assert "results" in data1
    assert len(data1["results"]) >= 2

    # Filter by method GET
    list2 = client.get("/api/v1/auditing/logs", {"method": "GET"})
    assert list2.status_code == 200
    data2 = list2.json()
    assert len(data2.get("results", [])) >= 2
    for item in data2["results"]:
        assert item["method"] == "GET"

    # Ordering by latest
    list3 = client.get("/api/v1/auditing/logs", {"ordering": "-created_at"})
    assert list3.status_code == 200
    data3 = list3.json()
    assert len(data3.get("results", [])) >= 2
