import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts_email_tokens",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    EXPIRES_SECONDS = 60 * 60 * 24  # 24h

    def is_expired(self):
        return (timezone.now() - self.created_at).total_seconds() > self.EXPIRES_SECONDS

    def mark_used(self):
        self.used = True
        self.save(update_fields=["used"])


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pw_tokens"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    EXPIRES_SECONDS = 60 * 60  # 1 hour

    def is_expired(self):
        return (timezone.now() - self.created_at).total_seconds() > self.EXPIRES_SECONDS

    def mark_used(self):
        self.used = True
        self.save(update_fields=["used"])


class BlacklistedToken(models.Model):
    jti = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.jti
