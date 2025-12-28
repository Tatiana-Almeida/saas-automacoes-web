from django.urls import path

from .views import (
    AuditLogListView,
    AuditRetentionPolicyDetailView,
    AuditRetentionPolicyListCreateView,
)

urlpatterns = [
    path("auditing/logs", AuditLogListView.as_view(), name="auditing-logs"),
    path(
        "auditing/retention-policies",
        AuditRetentionPolicyListCreateView.as_view(),
        name="auditing-retention-policies",
    ),
    path(
        "auditing/retention-policies/<int:policy_id>",
        AuditRetentionPolicyDetailView.as_view(),
        name="auditing-retention-policy-detail",
    ),
]
