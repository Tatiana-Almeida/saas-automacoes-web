from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationHistoryView, ReportsView, EventNotificationsView


router = DefaultRouter()
router.register(r'api/notifications', NotificationViewSet, basename='notification')


urlpatterns = [
    path('', include(router.urls)),
    path('api/notifications/history', NotificationHistoryView.as_view({'get':'list'}), name='notifications-history'),
    path('api/reports/summary', ReportsView.as_view(), name='reports-summary'),
    path('api/notifications/events', EventNotificationsView.as_view(), name='notifications-events'),
]
