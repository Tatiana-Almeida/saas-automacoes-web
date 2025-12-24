from pathlib import Path
from decouple import config, Csv
from datetime import timedelta
import dj_database_url
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='dev-insecure-key-change-me')
DEBUG = config('DEBUG', cast=bool, default=False)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default='127.0.0.1,localhost')

# Installed apps organized: Django core, third-party, then local apps
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'django_filters',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'whitenoise.runserver_nostatic',
]

LOCAL_APPS = [
    'starter.core',
    'starter.users',
    'starter.tenants',
    'starter.products',
    'starter.orders',
    'starter.automations',
    'starter.subscriptions',
    'starter.notifications',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    # Optional full-page caching (enable via CACHE_MIDDLEWARE_SECONDS > 0)
    # 'django.middleware.cache.UpdateCacheMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django.middleware.cache.FetchFromCacheMiddleware',
]

ROOT_URLCONF = 'starter.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'starter.wsgi.application'
ASGI_APPLICATION = 'starter.asgi.application'

# Database via DATABASE_URL or discrete vars
DATABASE_URL = config('DATABASE_URL', default='')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False),
    }
    DATABASES['default']['ATOMIC_REQUESTS'] = True
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='saas'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'ATOMIC_REQUESTS': True,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
# WhiteNoise for static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'SEARCH_PARAM': 'q',
    'DEFAULT_PAGINATION_CLASS': 'starter.api.pagination.DefaultPagination',
    'PAGE_SIZE': 12,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': config('DRF_THROTTLE_RATE_ANON', default='50/min'),
        'user': config('DRF_THROTTLE_RATE_USER', default='200/min'),
        'login': config('DRF_THROTTLE_RATE_LOGIN', default='10/min'),
    },
}

# SimpleJWT lifetimes via env
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('ACCESS_TOKEN_LIFETIME_MIN', cast=int, default=30)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('REFRESH_TOKEN_LIFETIME_DAYS', cast=int, default=7)),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS
CORS_ALLOW_CREDENTIALS = config('CORS_ALLOW_CREDENTIALS', cast=bool, default=True)
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=Csv(), default='http://localhost:3000,http://127.0.0.1:3000')
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', cast=Csv(), default='http://localhost:3000,http://127.0.0.1:3000')

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Email settings (env-driven)
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', cast=int, default=587)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool, default=True)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', cast=bool, default=False)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')

# Automations
AUTOMATIONS_DRY_RUN = config('AUTOMATIONS_DRY_RUN', cast=bool, default=True)

# Celery
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default=config('REDIS_URL', default='redis://localhost:6379/0'))
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default=config('REDIS_URL', default='redis://localhost:6379/0'))
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', cast=bool, default=False)
CELERY_TASK_TIME_LIMIT = config('CELERY_TASK_TIME_LIMIT', cast=int, default=300)
CELERY_BEAT_SCHEDULE = {
    'automations-scheduler-every-minute': {
        'task': 'starter.automations.tasks.schedule_automations_task',
        'schedule': 60.0,
    }
}

# Cache: Redis if available, else LocMem
REDIS_URL = config('REDIS_URL', default='')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'starter-locmem-cache',
        }
    }

# Cache middleware TTL (set >0 to enable Update/Fetch middleware pair in MIDDLEWARE)
CACHE_MIDDLEWARE_SECONDS = config('CACHE_MIDDLEWARE_SECONDS', cast=int, default=0)
CACHE_MIDDLEWARE_KEY_PREFIX = 'starter'

# Security headers (tuned via env in prod)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', cast=bool, default=False)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', cast=bool, default=False)
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', cast=bool, default=False)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', cast=int, default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', cast=bool, default=False)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', cast=bool, default=False)
SECURE_REFERRER_POLICY = config('SECURE_REFERRER_POLICY', default='same-origin')
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = config('X_FRAME_OPTIONS', default='DENY')

# Logging: separate app and security streams
LOG_LEVEL = config('LOG_LEVEL', default='INFO')
SECURITY_LOG_LEVEL = config('SECURITY_LOG_LEVEL', default='INFO')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{levelname}] {asctime} {name}: {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'fmt': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'security_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': True,
        },
        'security': {
            'handlers': ['security_console'],
            'level': SECURITY_LOG_LEVEL,
            'propagate': False,
        },
    },
}
