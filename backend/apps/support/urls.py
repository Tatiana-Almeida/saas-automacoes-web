from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SupportViewSet

router = DefaultRouter()
router.register(r"tickets", SupportViewSet, basename="support-ticket")

urlpatterns = [
    path("", include(router.urls)),
]
