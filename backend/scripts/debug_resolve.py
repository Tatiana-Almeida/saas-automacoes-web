import sys
from django.conf import settings
from django.urls import resolve, Resolver404
import django

django.setup()
print('ROOT_URLCONF:', settings.ROOT_URLCONF)
print('users in apps:', 'apps.users' in settings.INSTALLED_APPS)
path = sys.argv[1] if len(sys.argv) > 1 else '/api/v1/auth/token'
try:
    m = resolve(path)
    print('Resolved:', path, '->', m.route, 'name=', m.url_name)
except Resolver404 as e:
    print('Resolver404 for', path, e)
