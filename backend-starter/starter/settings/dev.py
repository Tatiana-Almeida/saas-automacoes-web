from .base import *  # noqa
from decouple import config

DEBUG = True
SECRET_KEY = config('SECRET_KEY', default='dev-insecure-key-change-me')

ALLOWED_HOSTS = ['*']

# Faster password hashing in dev
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = (  # type: ignore # noqa
    'rest_framework.permissions.AllowAny',
)
