from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AutomationViewSet, AutomationDashboardView


router = DefaultRouter()
router.register(r'api/automations', AutomationViewSet, basename='automation')


urlpatterns = [
    path('', include(router.urls)),
    path('api/automations/dashboard', AutomationDashboardView.as_view(), name='automations-dashboard'),
]
