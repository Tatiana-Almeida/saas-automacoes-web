import pytest
from django.contrib.auth import get_user_model
from django.core import mail


@pytest.mark.django_db
def test_register_sets_inactive_and_sends_email(client):
    url = "/api/v1/accounts/register/"
    data = {
        "email": "new@example.com",
        "password": "Str0ngPass!",
        "password_confirm": "Str0ngPass!",
    }
    resp = client.post(url, data, content_type="application/json")
    assert resp.status_code == 201
    User = get_user_model()
    u = User.objects.get(email__iexact="new@example.com")
    assert u.is_active is False
    # email sent
    assert len(mail.outbox) == 1
    assert "Confirm your account" in mail.outbox[0].subject
