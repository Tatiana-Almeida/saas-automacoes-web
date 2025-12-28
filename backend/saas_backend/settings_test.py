import os

from .settings import *

# Use SQLite in-memory DB for tests to avoid Postgres driver
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Optionally use a Docker Postgres instance for integration-style tests.
# To enable, set the environment variable `USE_DOCKER_POSTGRES=1` and
# `DATABASE_URL` (e.g. postgres://postgres:postgres@127.0.0.1:5432/saas).
if os.environ.get("USE_DOCKER_POSTGRES") == "1":
    DATABASES = {
        "default": env.db(
            "DATABASE_URL", default="postgres://postgres:postgres@127.0.0.1:5432/saas"
        )
    }
    # django-tenants requires the custom engine when using Postgres
    DATABASES["default"]["ENGINE"] = "django_tenants.postgresql_backend"
    DATABASES["default"]["ATOMIC_REQUESTS"] = True

# Disable tenant-specific DB routing for tests
DATABASE_ROUTERS = []

# Remove tenant-dependent middleware to simplify test stack
_REMOVE_MIDDLEWARE = {
    "django_tenants.middleware.main.TenantMainMiddleware",
    "apps.core.middleware.EnsureTenantSetMiddleware",
    "apps.core.middleware.EnforceActiveTenantMiddleware",
    "apps.core.middleware.TenantMainMiddleware",
    "apps.core.middleware.TenantContextMiddleware",
    "apps.core.middleware.PlanLimitMiddleware",
    "apps.rbac.middleware.PermissionMiddleware",
}
MIDDLEWARE = [mw for mw in MIDDLEWARE if mw not in _REMOVE_MIDDLEWARE]

# Reduce throttle rates to keep tests snappy
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}),
        "anon": "1000/min",
        "user": "1000/min",
        "auth_login": "1000/min",
        "auth_register": "1000/min",
        "auth_logout": "1000/min",
        "auth_refresh": "1000/min",
    },
}

# Disable throttle classes in tests to avoid accidental 429s unless specifically tested
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ()

# During tests, use session auth to allow `Client.force_login()` to work with DRF views.
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = (
    "apps.core.authentication.CookieJWTAuthentication",
    "rest_framework.authentication.SessionAuthentication",
    "rest_framework.authentication.BasicAuthentication",
)

# Exclude django-tenants to avoid Postgres-specific middleware; keep tenants app for model availability
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "django_tenants"]

# Ensure local `accounts` app is available during tests
INSTALLED_APPS = INSTALLED_APPS + [
    "accounts",
]

# Use a minimal URL conf for tests to avoid tenants imports
ROOT_URLCONF = "saas_backend.urls_test"
PUBLIC_SCHEMA_URLCONF = "saas_backend.urls_test"

# Keep migrations enabled for core apps so DB tables exist in tests.
# Only disable migrations for local test-only apps if necessary.
MIGRATION_MODULES = {}

# For SQLite-based test runs, disable migrations for apps that do not provide
# explicit migration files so Django will create tables directly from models.
MIGRATION_MODULES.update(
    {
        "tenants": None,
        "rbac": None,
        "auditing": None,
        "users": None,
        "support": None,
        "core": None,
    }
)

# Optionally disable migrations for `accounts` to speed tests
MIGRATION_MODULES["accounts"] = None

# Ensure Celery tasks run synchronously during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use local memory cache for tests to avoid Redis dependency
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Allow all hosts in test environment to avoid DisallowedHost on custom domains
ALLOWED_HOSTS = ["*"]

# Signal to code that we're running tests
TESTING = True
