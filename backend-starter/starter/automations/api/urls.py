from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AutomationDashboardView, AutomationViewSet

router = DefaultRouter()
router.register(r"api/automations", AutomationViewSet, basename="automation")


urlpatterns = [
    path("", include(router.urls)),
    path(
        "api/automations/dashboard",
        AutomationDashboardView.as_view(),
        name="automations-dashboard",
    ),
]
