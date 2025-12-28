from django.conf import settings
from django.db import models


class SupportTicket(models.Model):
    STATUS_OPEN = "open"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_RESOLVED = "resolved"

    STATUS_CHOICES = (
        (STATUS_OPEN, "Aberto"),
        (STATUS_IN_PROGRESS, "Em andamento"),
        (STATUS_RESOLVED, "Resolvido"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="support_tickets",
    )
    email = models.EmailField(blank=True, null=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default=STATUS_OPEN
    )
    response = models.TextField(blank=True, null=True)
    responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="support_responses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Support Ticket"
        verbose_name_plural = "Support Tickets"

    def __str__(self):
        return f"#{self.id} {self.subject} ({self.status})"
