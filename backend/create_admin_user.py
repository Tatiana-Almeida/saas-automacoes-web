"""Utility to create an admin user for local development/tests."""
# ruff: noqa: E402
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saas_backend.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get("ADMIN_USERNAME", "admin")
email = os.environ.get("ADMIN_EMAIL", "admin@example.com")

# Prefer secure password from environment; otherwise generate a strong one
password = os.environ.get("ADMIN_PASSWORD")
if not password:
    import secrets

    password = secrets.token_urlsafe(24)

user, created = User.objects.get_or_create(
    username=username, defaults={"email": email, "is_staff": True, "is_superuser": True}
)
if not created:
    user.is_staff = True
    user.is_superuser = True
user.set_password(password)
user.save()
