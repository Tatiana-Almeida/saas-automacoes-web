import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_change_password_and_invalidate_refresh(client):
    User = get_user_model()
    u = User.objects.create(email="cp@example.com", is_active=True)
    u.set_password("OldPass123!")
    u.save()
    r = client.post(
        "/api/v1/accounts/login/",
        {"email": "cp@example.com", "password": "OldPass123!"},
        content_type="application/json",
    )
    assert r.status_code == 200
    tokens = r.json()
    refresh = tokens["refresh"]
    # change password and blacklist refresh
    cp = client.post(
        "/api/v1/accounts/change-password/",
        {
            "current_password": "OldPass123!",
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
            "refresh": refresh,
        },
        content_type="application/json",
    )
    assert cp.status_code == 200
    # old refresh should now be invalid
    rf = client.post(
        "/api/v1/accounts/token/refresh/",
        {"refresh": refresh},
        content_type="application/json",
    )
    assert rf.status_code in (400, 401)
