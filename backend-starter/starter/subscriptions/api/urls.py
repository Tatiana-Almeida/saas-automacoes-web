from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SubscriptionViewSet

router = DefaultRouter()
router.register(r"api/subscriptions", SubscriptionViewSet, basename="subscription")


urlpatterns = [
    path("", include(router.urls)),
]
