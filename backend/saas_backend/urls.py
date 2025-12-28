from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view as get_yasg_schema_view
from rest_framework.permissions import AllowAny

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # drf-yasg (Swagger/OpenAPI)
    path(
        "api/swagger(.json|.yaml)",
        get_yasg_schema_view(
            openapi.Info(
                title="SaaS Automacoes API",
                default_version="v1",
                description="Documentação Swagger gerada por drf-yasg",
            ),
            public=True,
            permission_classes=(AllowAny,),
        ).without_ui(cache_timeout=0),
        name="yasg-schema-json",
    ),
    path(
        "api/swagger/",
        get_yasg_schema_view(
            openapi.Info(
                title="SaaS Automacoes API",
                default_version="v1",
                description="Documentação Swagger gerada por drf-yasg",
            ),
            public=True,
            permission_classes=(AllowAny,),
        ).with_ui("swagger", cache_timeout=0),
        name="yasg-swagger-ui",
    ),
    path(
        "api/redoc/",
        get_yasg_schema_view(
            openapi.Info(
                title="SaaS Automacoes API",
                default_version="v1",
                description="Documentação ReDoc gerada por drf-yasg",
            ),
            public=True,
            permission_classes=(AllowAny,),
        ).with_ui("redoc", cache_timeout=0),
        name="yasg-redoc",
    ),
    path("api/v1/core/", include("apps.core.urls")),
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/", include("apps.whatsapp.urls")),
    path("api/v1/", include("apps.mailer.urls")),
    path("api/v1/", include("apps.sms.urls")),
    path("api/v1/", include("apps.chatbots.urls")),
    path("api/v1/", include("apps.workflows.urls")),
    path("api/v1/", include("apps.ai.urls")),
    path("api/v1/", include("apps.auditing.urls")),
    path("api/v1/", include("apps.tenants.urls")),
    path("api/v1/", include("apps.rbac.urls")),
    path("api/v1/support/", include("apps.support.urls")),
    # Landing page
    path("", TemplateView.as_view(template_name="landing.html"), name="landing"),
]
