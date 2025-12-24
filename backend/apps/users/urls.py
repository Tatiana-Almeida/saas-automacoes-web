from django.urls import path
from .views import (
    ProfileView,
    AdminPingView,
    RegisterView,
    LogoutView,
    CustomTokenObtainPairView,
    ThrottledTokenRefreshView,
)
from .urls_password import urlpatterns as pwd_urls

urlpatterns = [
    path('auth/register', RegisterView.as_view(), name='auth_register'),
    path('auth/token', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh', ThrottledTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout', LogoutView.as_view(), name='auth_logout'),
    path('users/me', ProfileView.as_view(), name='users_me'),
    path('admin/ping', AdminPingView.as_view(), name='admin_ping'),
]

# password reset urls
urlpatterns += pwd_urls
 
