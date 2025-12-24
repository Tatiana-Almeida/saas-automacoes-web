from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from starter.users.auth import EmailTokenObtainPairView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Health
    path('', include('starter.core.urls')),
    # Auth (JWT)
    path('api/auth/token/', EmailTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Users
    path('', include('starter.users.api.urls')),
    # Tenants
    path('', include('starter.tenants.api.urls')),
    # E-commerce apps
    path('', include('starter.products.api.urls')),
    path('', include('starter.orders.api.urls')),
    path('', include('starter.automations.api.urls')),
    path('', include('starter.subscriptions.api.urls')),
    path('', include('starter.notifications.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
