from django.conf import settings
from django.db import models


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"
    WHATSAPP = "whatsapp", "WhatsApp"


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    channel = models.CharField(max_length=16, choices=NotificationChannel.choices)
    to = models.CharField(max_length=255, help_text="Email, phone, or WhatsApp number")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.channel}: {self.title} -> {self.to} ({self.status})"


class NotificationLog(models.Model):
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="logs"
    )
    status = models.CharField(max_length=16, choices=NotificationStatus.choices)
    attempt = models.PositiveIntegerField(default=1)
    message = models.TextField(blank=True, null=True)
    response_payload = models.JSONField(default=dict, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Log({self.notification_id}, {self.status}, attempt={self.attempt})"
