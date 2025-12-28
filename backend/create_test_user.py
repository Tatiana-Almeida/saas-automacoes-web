import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saas_backend.settings")
django.setup()

# ruff: noqa: E402
from django.contrib.auth import get_user_model

User = get_user_model()

# Create or update test user without hardcoded secrets
username = os.environ.get("TEST_USER_USERNAME", "testuser")
password = os.environ.get("TEST_USER_PASSWORD")
if not password:
    import secrets

    password = secrets.token_urlsafe(16)

user, created = User.objects.get_or_create(username=username)
user.set_password(password)
user.save()

if created:
    pass
else:
    pass
