from django.conf import settings
from django.db import models


class SubscriptionStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    CANCELED = 'canceled', 'Canceled'
    PAST_DUE = 'past_due', 'Past due'


class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.user} - {self.plan} ({self.status})"
