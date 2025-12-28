import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

# Reduce middleware in tests to avoid django-tenants middleware requiring
# a tenant-aware DB connection in this unit test environment.
TEST_MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]


User = get_user_model()


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_register_valid():
    client = APIClient()
    payload = {
        "email": "newuser@example.com",
        "nome_completo": "New User",
        "password": "Str0ngP@ssword!",
        "password_confirm": "Str0ngP@ssword!",
    }
    resp = client.post("/api/v1/auth/register/", payload, format="json")
    assert resp.status_code == 201
    assert "id" in resp.data
    # user is created but inactive
    user = User.objects.filter(email__iexact=payload["email"]).first()
    assert user is not None
    assert user.is_active is False


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_register_duplicate_email():
    # create existing user
    User.objects.create_user(email="dup@example.com", password="TempPass123")
    client = APIClient()
    payload = {
        "email": "dup@example.com",
        "nome_completo": "Dup User",
        "password": "An0ther$Pass",
        "password_confirm": "An0ther$Pass",
    }
    resp = client.post("/api/v1/auth/register/", payload, format="json")
    assert resp.status_code == 400
    assert "email" in resp.data.get("error", {}).get("details", {})


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_register_weak_password_rejected():
    client = APIClient()
    payload = {
        "email": "weakpw@example.com",
        "nome_completo": "Weak PW",
        # 'password' is a common weak password and should be rejected by validators
        "password": "password",
        "password_confirm": "password",
    }
    resp = client.post("/api/v1/auth/register/", payload, format="json")
    assert resp.status_code == 400
    # password validator errors should be returned under 'password'
    assert "password" in resp.data.get("error", {}).get("details", {})


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_register_password_mismatch():
    client = APIClient()
    payload = {
        "email": "mismatch@example.com",
        "nome_completo": "Mismatch",
        "password": "Str0ngP@ss1",
        "password_confirm": "DifferentP@ss2",
    }
    resp = client.post("/api/v1/auth/register/", payload, format="json")
    assert resp.status_code == 400
    assert "password_confirm" in resp.data.get("error", {}).get("details", {})


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_confirm_email_activates_user():
    client = APIClient()
    payload = {
        "email": "confirmme@example.com",
        "nome_completo": "To Confirm",
        "password": "Str0ngP@ssword!",
        "password_confirm": "Str0ngP@ssword!",
    }
    resp = client.post("/api/v1/auth/register/", payload, format="json")
    assert resp.status_code == 201
    user = User.objects.get(email__iexact=payload["email"])
    # find token
    token_obj = user.email_tokens.first()
    assert token_obj is not None
    # confirm
    resp2 = client.post(
        "/api/v1/auth/confirm-email/", {"token": str(token_obj.token)}, format="json"
    )
    assert resp2.status_code == 200
    user.refresh_from_db()
    assert user.is_active is True


@pytest.mark.django_db
@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
def test_confirm_email_invalid_token():
    client = APIClient()
    resp = client.post(
        "/api/v1/auth/confirm-email/",
        {"token": "00000000-0000-0000-0000-000000000000"},
        format="json",
    )
    assert resp.status_code == 400
