from .settings import *

# Postgres test DB config (override via env if needed)
DATABASES = {
    "default": env.db(
        "DATABASE_URL_TEST_PG",
        default="postgres://root:1234567890@localhost:5432/saas_test",
    )
}
DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# Use full URLConf including tenants/RBAC endpoints
ROOT_URLCONF = "saas_backend.urls"
PUBLIC_SCHEMA_URLCONF = "saas_backend.urls"

# Ensure Celery tasks run synchronously during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Keep django-tenants routing and apps from base settings
# (SHARED_APPS + TENANT_APPS already compose INSTALLED_APPS in base)
# Explicit tenant model declarations for clarity
TENANT_MODEL = "tenants.Tenant"
DOMAIN_MODEL = "tenants.Domain"
TENANT_DOMAIN_MODEL = DOMAIN_MODEL

# Optionally relax throttles during tests
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),
        "anon": "1000/min",
        "user": "1000/min",
        "auth_login": "50/min",
        "auth_register": "50/min",
        "auth_refresh": "100/min",
        "auth_logout": "100/min",
    },
}

# When no tenant Domain is found for the request hostname during tests,
# serve from the public schema instead of raising a 404 so endpoint tests
# that don't depend on a specific tenant can run under Postgres.
SHOW_PUBLIC_IF_NO_TENANT_FOUND = True
