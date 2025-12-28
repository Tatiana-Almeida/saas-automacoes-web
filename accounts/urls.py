from django.urls import path

from .views import (
    ChangePasswordView,
    ConfirmEmailView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ProfileView,
    RegisterView,
    TokenRefreshView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="accounts-register"),
    path("confirm-email/", ConfirmEmailView.as_view(), name="accounts-confirm"),
    path("login/", LoginView.as_view(), name="accounts-login"),
    path("logout/", LogoutView.as_view(), name="accounts-logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="accounts-token-refresh"),
    path(
        "reset-password/",
        PasswordResetRequestView.as_view(),
        name="accounts-reset-request",
    ),
    path(
        "reset-password/confirm/",
        PasswordResetConfirmView.as_view(),
        name="accounts-reset-confirm",
    ),
    path("me/", ProfileView.as_view(), name="accounts-profile"),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="accounts-change-password",
    ),
]
