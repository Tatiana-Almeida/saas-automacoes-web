import pytest
from django.contrib.auth import get_user_model
from django.core import mail


@pytest.mark.django_db
def test_password_reset_flow(client):
    User = get_user_model()
    u = User.objects.create(email="pw@example.com", is_active=True)
    u.set_password("OldPass123!")
    u.save()
    # request reset
    r = client.post(
        "/api/v1/accounts/reset-password/",
        {"email": "pw@example.com"},
        content_type="application/json",
    )
    assert r.status_code == 200
    assert len(mail.outbox) == 1
    body = mail.outbox[0].body
    import re

    m = re.search(r"token=([0-9a-fA-F-]+)", body)
    assert m
    token = m.group(1)
    # confirm reset
    cr = client.post(
        "/api/v1/accounts/reset-password/confirm/",
        {
            "token": token,
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        },
        content_type="application/json",
    )
    assert cr.status_code == 200
    u.refresh_from_db()
    assert u.check_password("NewPass123!")
