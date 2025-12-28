from django.urls import path

from .views import (
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    me,
)

urlpatterns = [
    path("api/users/me", me, name="users-me"),
    path("api/auth/register", RegisterView.as_view(), name="auth-register"),
    path("api/auth/logout", LogoutView.as_view(), name="auth-logout"),
    path(
        "api/auth/password-reset",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset",
    ),
    path(
        "api/auth/password-reset/confirm",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]
