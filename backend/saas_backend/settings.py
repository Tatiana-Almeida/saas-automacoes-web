import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

environ.Env.read_env(env_file=os.path.join(BASE_DIR, ".env"))

DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY", default="dev-secret-change-me")
ALLOWED_HOSTS = [
    h.strip()
    for h in env(
        "ALLOWED_HOSTS", default="127.0.0.1,localhost,.localhost,testserver"
    ).split(",")
]

# During test runs (pytest) allow all hosts to avoid DisallowedHost when
# tests use custom domain names like 'tenant.localhost'. We detect pytest
# via sys.argv which is sufficient for our test invocation path used here.
import sys

try:
    if any("pytest" in str(a) for a in sys.argv):
        ALLOWED_HOSTS = ["*"]
except Exception:
    pass

TENANT_DEFAULT_SCHEMA_NAME = env("TENANT_DEFAULT_SCHEMA_NAME", default="public")

INSTALLED_APPS = []  # Will be computed after SHARED_APPS and TENANT_APPS definitions

SHARED_APPS = (
    "django_tenants",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.tenants",  # must be in shared
    "apps.users",
    "apps.rbac",
    "rest_framework_simplejwt.token_blacklist",
    "apps.auditing",
)

TENANT_APPS = (
    "rest_framework",
    "drf_spectacular",
    "drf_yasg",
    "apps.core",
    "apps.support",
    # 'apps.users' moved to SHARED_APPS since the project uses a shared auth model
    "apps.whatsapp",
    "apps.mailer",
    "apps.sms",
    "apps.chatbots",
    "apps.workflows",
    "apps.ai",
)

TENANT_MODEL = "tenants.Tenant"
DOMAIN_MODEL = "tenants.Domain"
# Compatibility for django-tenants versions expecting TENANT_DOMAIN_MODEL
TENANT_DOMAIN_MODEL = DOMAIN_MODEL

# IMPORTANT: django-tenants requires INSTALLED_APPS to be the concatenation
# of SHARED_APPS and TENANT_APPS to route migrations correctly.
INSTALLED_APPS = list(SHARED_APPS) + list(TENANT_APPS)

# Use custom user model (app_label.ModelName form)
AUTH_USER_MODEL = "users.User"

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

MIDDLEWARE = [
    "apps.core.middleware.InitialRequestDebugMiddleware",
    # EnsureTenantSetMiddleware must run before django-tenants' TenantMainMiddleware
    # so tests that register an in-process domain mapping can resolve the
    # tenant prior to django-tenants changing the URLConf/search_path.
    "apps.core.middleware.EnsureTenantSetMiddleware",
    "apps.core.middleware.TenantMainMiddleware",
    "apps.core.middleware.RequestDebugMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.rbac.middleware.PermissionMiddleware",
    "apps.core.middleware.EnforceActiveTenantMiddleware",
    "apps.core.middleware.PlanLimitMiddleware",
    "apps.core.middleware.TenantContextMiddleware",
    "apps.auditing.middleware.AuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "saas_backend.urls"
PUBLIC_SCHEMA_URLCONF = "saas_backend.urls"

# During tests and some development flows, prefer showing public urls instead
# of raising 404 immediately when a tenant is not found. This allows
# fallback middleware to attempt tenant resolution (useful for integration
# tests that create Domain/Tenant entries dynamically).
SHOW_PUBLIC_IF_NO_TENANT_FOUND = True

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "saas_backend.context_processors.analytics",
            ],
        },
    },
]

WSGI_APPLICATION = "saas_backend.wsgi.application"
ASGI_APPLICATION = "saas_backend.asgi.application"

DATABASE_URL = env(
    "DATABASE_URL", default="postgres://postgres:postgres@postgres:5432/saas"
)
# Parse DATABASE_URL when provided; this ensures host/port/user are taken from
# the environment inside containers (compose sets DATABASE_URL to use service
# hostnames like `postgres`). Then set the django-tenants engine and sensible
# local defaults for user/password/test DB.
default_db = env.db("DATABASE_URL", default=DATABASE_URL)
default_db["ENGINE"] = "django_tenants.postgresql_backend"
default_db.setdefault("NAME", "saas_automacoes_web")
default_db.setdefault("USER", "saas_user")
default_db.setdefault("PASSWORD", "1234567890")
default_db.setdefault("PORT", "5432")
default_db.setdefault("TEST", {"NAME": "test_saas_automacoes_web"})

DATABASES = {"default": default_db}

# Ensure host picks up the DB_HOST override when provided; default to the
# compose service name so containerized processes resolve Postgres correctly.
DATABASES["default"]["HOST"] = env("DB_HOST", default="postgres")

# Required DB engine for django-tenants
DATABASES["default"]["ATOMIC_REQUESTS"] = True

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Security / Production toggles ---
IS_PRODUCTION = env.bool("IS_PRODUCTION", default=False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if IS_PRODUCTION else None
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=IS_PRODUCTION)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=IS_PRODUCTION)
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=IS_PRODUCTION)
SECURE_HSTS_SECONDS = env.int(
    "SECURE_HSTS_SECONDS", default=(31536000 if IS_PRODUCTION else 0)
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=IS_PRODUCTION
)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=IS_PRODUCTION)
SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", default="same-origin")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.core.authentication.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": (
        "apps.core.renderers.StandardJSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "apps.core.throttling.PlanScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/min",
        "user": "60/min",
        "auth_login": "5/min",
        "auth_register": "3/min",
        "auth_refresh": "10/min",
        "auth_logout": "10/min",
    },
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "saas_backend.exceptions.custom_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SaaS Automacoes API",
    "VERSION": "v1",
    "SERVE_INCLUDE_SCHEMA": False,
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Cache backend (Redis recommended for throttle counters and multi-worker)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Celery configuration
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_ROUTES = {
    "apps.events.tasks.handle_event": {"queue": "events"},
    "apps.events.tasks.dead_letter_event": {"queue": "dlq"},
}
CELERY_BEAT_SCHEDULE = {
    "check-daily-limit-warns": {
        "task": "apps.core.tasks.check_daily_limit_warns",
        # Run every 10 minutes
        "schedule": 600,
    },
    "export-audit-logs": {
        "task": "apps.auditing.tasks.export_audit_logs_to_elasticsearch",
        # Run every 5 minutes; task self-disables if not enabled
        "schedule": 300,
    },
    "purge-dlq-daily": {
        "task": "apps.auditing.tasks.purge_dlq_older_than_default",
        # Run once per day
        "schedule": 24 * 3600,
    },
}

# DLQ purge default (days)
AUDIT_DLQ_PURGE_DAYS = env.int("AUDIT_DLQ_PURGE_DAYS", default=30)

# Per-tenant plan throttling rates for scoped endpoints
TENANT_PLAN_THROTTLE_RATES = {
    "free": {
        "send_whatsapp": "10/min",
        "send_email": "20/min",
        "send_sms": "10/min",
        "chatbots_send": "30/min",
        "workflows_execute": "15/min",
        "ai_infer": "5/min",
    },
    "pro": {
        "send_whatsapp": "200/min",
        "email_send": "500/min",
        "sms_send": "300/min",
        "chatbots_send": "600/min",
        "workflows_execute": "200/min",
        "ai_infer": "60/min",
    },
    "enterprise": {
        "send_whatsapp": "2000/min",
        "email_send": "5000/min",
        "sms_send": "3000/min",
        "chatbots_send": "6000/min",
        "workflows_execute": "2000/min",
        "ai_infer": "600/min",
    },
}

# Limites diários por plano para ações (validação extra antes de executar)
TENANT_PLAN_DAILY_LIMITS = {
    "free": {
        "send_whatsapp": 100,
        "send_email": 300,
        "send_sms": 100,
        "chatbots_send": 300,
        "workflows_execute": 100,
        "ai_infer": 50,
    },
    "pro": {
        "send_whatsapp": 5000,
        "email_send": 15000,
        "sms_send": 8000,
        "chatbots_send": 20000,
        "workflows_execute": 5000,
        "ai_infer": 2000,
    },
    "enterprise": {
        "send_whatsapp": 50000,
        "email_send": 150000,
        "sms_send": 80000,
        "chatbots_send": 200000,
        "workflows_execute": 50000,
        "ai_infer": 20000,
    },
}

# Warn threshold for daily usage percent in summary (0-100)
TENANT_PLAN_DAILY_WARN_THRESHOLD = env.int(
    "TENANT_PLAN_DAILY_WARN_THRESHOLD", default=80
)

# Optional: send near-limit alerts to this email (if set)
TENANT_ALERTS_EMAIL_TO = env("TENANT_ALERTS_EMAIL_TO", default=None)

# Logging: console output; optionally structured for ELK
DJANGO_LOG_LEVEL = env("DJANGO_LOG_LEVEL", default="INFO")
USE_JSON_LOGS = env.bool("USE_JSON_LOGS", default=False)

_formatters = {"standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}}
if USE_JSON_LOGS:
    _formatters["json"] = {"()": "apps.core.logging_utils.JSONFormatter"}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": _formatters,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if USE_JSON_LOGS else "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": DJANGO_LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": False,
        },
    },
}

# Webhook verification
# Map provider -> secret; set via environment
# Examples supported: stripe, paypal, custom
WEBHOOK_SECRETS = {
    "stripe": env("STRIPE_WEBHOOK_SECRET", default=None),
    "paypal": env("PAYPAL_WEBHOOK_SECRET", default=None),
    "custom": env("CUSTOM_WEBHOOK_SECRET", default=None),
}
WEBHOOK_MAX_SKEW_SECONDS = env.int("WEBHOOK_MAX_SKEW_SECONDS", default=300)
WEBHOOK_IDEMPOTENCY_TTL_SECONDS = env.int(
    "WEBHOOK_IDEMPOTENCY_TTL_SECONDS", default=86400
)

# Optional Elasticsearch export for AuditLog
AUDIT_EXPORT_ENABLED = env.bool("AUDIT_EXPORT_ENABLED", default=False)
ELASTICSEARCH_URL = env("ELASTICSEARCH_URL", default=None)
AUDIT_EXPORT_INDEX_PREFIX = env("AUDIT_EXPORT_INDEX_PREFIX", default="audit")
ELASTICSEARCH_USERNAME = env("ELASTICSEARCH_USERNAME", default=None)
ELASTICSEARCH_PASSWORD = env("ELASTICSEARCH_PASSWORD", default=None)
ELASTICSEARCH_API_KEY = env("ELASTICSEARCH_API_KEY", default=None)

# Webhook alerts for critical audit actions
ALERT_WEBHOOK_ENABLED = env.bool("ALERT_WEBHOOK_ENABLED", default=False)
ALERT_WEBHOOK_URL = env("ALERT_WEBHOOK_URL", default=None)
AUDIT_CRITICAL_ACTIONS = env.list(
    "AUDIT_CRITICAL_ACTIONS",
    default=["rbac_change", "plan_change", "suspend_tenant", "reactivate_tenant"],
)
ALERT_WEBHOOK_QUIET_MINUTES = env.int("ALERT_WEBHOOK_QUIET_MINUTES", default=10)
ALERT_WEBHOOK_QUIET_BYPASS_ACTIONS = env.list(
    "ALERT_WEBHOOK_QUIET_BYPASS_ACTIONS", default=[]
)

# JWT cookie settings
JWT_COOKIE_NAME = env("JWT_COOKIE_NAME", default="access_token")
JWT_COOKIE_SECURE = env.bool("JWT_COOKIE_SECURE", default=False)
JWT_COOKIE_HTTPONLY = True
JWT_COOKIE_SAMESITE = env(
    "JWT_COOKIE_SAMESITE", default="Lax"
)  # 'Lax' | 'None' | 'Strict'
JWT_COOKIE_DOMAIN = env("JWT_COOKIE_DOMAIN", default=None)

# Optional view-level cache TTLs (seconds); 0 disables caching
CACHE_TTL_TENANT_STATUS = env.int("CACHE_TTL_TENANT_STATUS", default=0)
CACHE_TTL_TENANT_DAILY_SUMMARY = env.int("CACHE_TTL_TENANT_DAILY_SUMMARY", default=0)

# Audit retention (default + per-tenant overrides)
AUDIT_RETENTION_DEFAULT_DAYS = env.int("AUDIT_RETENTION_DEFAULT_DAYS", default=90)
# Map tenant schema_name -> days (set in settings.py or via environment by importing/overriding)
AUDIT_RETENTION_TENANT_DAYS = {}

# Google Analytics / Marketing integration
# Set GA_TRACKING_ID (e.g. G-XXXXXXXXXX) to enable client-side tracking in templates.
# For server-side Measurement Protocol events, set GA_MEASUREMENT_ID and GA_API_SECRET.
GA_TRACKING_ID = env("GA_TRACKING_ID", default=None)
GA_MEASUREMENT_ID = env("GA_MEASUREMENT_ID", default=None)
GA_API_SECRET = env("GA_API_SECRET", default=None)

# Password reset token lifetime (seconds). Default 30 minutes.
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT_SECONDS", default=1800)
