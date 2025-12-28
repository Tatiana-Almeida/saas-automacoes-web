import pytest
from django.contrib.auth import get_user_model
from django.core import mail


@pytest.mark.django_db
def test_confirm_email_activates_user(client):
    # register first
    reg = client.post(
        "/api/v1/accounts/register/",
        {
            "email": "verify@example.com",
            "password": "Str0ngPass!",
            "password_confirm": "Str0ngPass!",
        },
        content_type="application/json",
    )
    assert reg.status_code == 201
    assert len(mail.outbox) == 1
    # extract token from email body
    body = mail.outbox[0].body
    import re

    m = re.search(r"token=([0-9a-fA-F-]+)", body)
    assert m
    token = m.group(1)
    resp = client.post(
        "/api/v1/accounts/confirm-email/",
        {"token": token},
        content_type="application/json",
    )
    assert resp.status_code == 200
    User = get_user_model()
    u = User.objects.get(email__iexact="verify@example.com")
    assert u.is_active is True
