import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_login_returns_tokens(client):
    User = get_user_model()
    u = User.objects.create(email="login@example.com", is_active=True)
    u.set_password("Str0ngPass!")
    u.save()
    resp = client.post(
        "/api/v1/accounts/login/",
        {"email": "login@example.com", "password": "Str0ngPass!"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access" in body and "refresh" in body
