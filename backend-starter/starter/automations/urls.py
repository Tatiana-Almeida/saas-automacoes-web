from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AutomationViewSet


router = DefaultRouter()
router.register(r'api/automations', AutomationViewSet, basename='automation')


urlpatterns = [
    path('', include(router.urls)),
]
