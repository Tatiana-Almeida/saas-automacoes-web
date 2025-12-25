from django.urls import path
from .views import (
    HealthView,
    TenantThrottleStatusView,
    ResetDailyPlanCountersView,
    TenantDailySummaryView,
    QueuesStatusView,
    WebhookReceiverView,
)

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path(
        "throttle/status",
        TenantThrottleStatusView.as_view(),
        name="tenant_throttle_status",
    ),
    path(
        "throttle/daily/reset",
        ResetDailyPlanCountersView.as_view(),
        name="tenant_daily_reset",
    ),
    path(
        "throttle/daily/summary",
        TenantDailySummaryView.as_view(),
        name="tenant_daily_summary",
    ),
    path("queues/status", QueuesStatusView.as_view(), name="queues_status"),
    path(
        "webhooks/<str:provider>",
        WebhookReceiverView.as_view(),
        name="webhook_receiver",
    ),
]
