from django.urls import path
from .views import TenantCreateView, TenantActionView, TenantPlanUpdateView

urlpatterns = [
    path('tenants', TenantCreateView.as_view(), name='tenant-create'),
    path('tenants/<int:tenant_id>/actions', TenantActionView.as_view(), name='tenant-action'),
    path('tenants/<int:tenant_id>/plan', TenantPlanUpdateView.as_view(), name='tenant-plan-update'),
]
