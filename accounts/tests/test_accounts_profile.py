import pytest
from django.contrib.auth import get_user_model
from django.core import mail


@pytest.mark.django_db
def test_profile_get_and_update_email_requires_verification(client):
    User = get_user_model()
    u = User.objects.create(email="profile@example.com", is_active=True)
    u.set_password("Pwd12345!")
    u.save()
    # login
    r = client.post(
        "/api/v1/accounts/login/",
        {"email": "profile@example.com", "password": "Pwd12345!"},
        content_type="application/json",
    )
    tokens = r.json()
    access = tokens["access"]
    # get profile
    g = client.get("/api/v1/accounts/me/", HTTP_AUTHORIZATION=f"Bearer {access}")
    assert g.status_code == 200
    # update email
    up = client.put(
        "/api/v1/accounts/me/",
        {"email": "newprofile@example.com", "nome_completo": "Nome"},
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )
    assert up.status_code in (200, 204)
    # user should be inactive until verify
    u.refresh_from_db()
    assert u.is_active is False
    assert len(mail.outbox) == 1
