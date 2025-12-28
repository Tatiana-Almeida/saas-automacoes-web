from django.urls import include, path

urlpatterns = [
    # Minimal URLs required for unit tests
    path("api/v1/core/", include("apps.core.urls")),
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/accounts/", include("accounts.urls")),
    path("api/v1/", include("apps.auditing.urls")),
    path("api/v1/support/", include("apps.support.urls")),
    path("api/v1/", include("apps.rbac.urls")),
]
