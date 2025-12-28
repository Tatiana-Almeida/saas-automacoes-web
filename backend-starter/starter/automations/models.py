from django.conf import settings
from django.db import models
from django.utils import timezone


class AutomationType(models.TextChoices):
    WEBHOOK = "webhook", "Webhook"
    WHATSAPP = "whatsapp", "WhatsApp"
    EMAIL = "email", "Email"


class Automation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="automations"
    )
    name = models.CharField(max_length=200)
    type = models.CharField(
        max_length=32, choices=AutomationType.choices, default=AutomationType.WEBHOOK
    )
    is_active = models.BooleanField(default=True)
    configuration = models.JSONField(default=dict, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=16, null=True, blank=True)
    last_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = (
            "-updated_at",
            "name",
        )

    def __str__(self) -> str:
        return f"{self.name} ({self.get_type_display()})"

    def activate(self):
        self.is_active = True
        self.save(update_fields=["is_active", "updated_at"])

    def pause(self):
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])


class AutomationRunStatus(models.TextChoices):
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    STARTED = "started", "Started"


class AutomationLog(models.Model):
    automation = models.ForeignKey(
        Automation, on_delete=models.CASCADE, related_name="logs"
    )
    status = models.CharField(max_length=16, choices=AutomationRunStatus.choices)
    error_message = models.TextField(blank=True, null=True)
    output_payload = models.JSONField(default=dict, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"AutomationLog({self.automation_id}, {self.status}, {self.created_at})"

    @property
    def duration_ms(self):
        if self.finished_at and self.started_at:
            delta = self.finished_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None
