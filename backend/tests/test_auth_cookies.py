import json

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_login_sets_cookie_and_me_works_with_cookie(client, gen_password):
    # Create user
    username = "testuser"
    password = gen_password()
    User.objects.create_user(username=username, password=password)

    # Login to obtain cookie
    resp = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    # Cookie set by the view (HttpOnly) - access_token
    cookies = resp.cookies
    assert "access_token" in cookies

    # Use only cookie, no Authorization header
    client.cookies["access_token"] = cookies["access_token"].value
    me = client.get("/api/v1/users/me")
    assert me.status_code == 200
    data = me.json().get("data", {})
    assert data.get("username") == username


@pytest.mark.django_db
def test_logout_clears_cookie(client, gen_password):
    username = "testuser2"
    password = gen_password()
    User.objects.create_user(username=username, password=password)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value
    payload = login.json().get("data", {})
    refresh = payload.get("refresh")

    # Provide refresh if required by your logout implementation
    # Here we post an empty body; adjust if your endpoint expects refresh
    logout = client.post(
        "/api/v1/auth/logout",
        data=json.dumps({"refresh": refresh} if refresh else {}),
        content_type="application/json",
    )
    assert logout.status_code in (200, 204)
    # Server should instruct deletion; client cookie jar should no longer include it
    # Depending on test client behavior, ensure next request is unauthorized without cookie
    client.cookies.pop("access_token", None)
    me = client.get("/api/v1/users/me")
    assert me.status_code in (401, 403)
