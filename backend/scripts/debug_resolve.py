import sys

import django
from django.urls import Resolver404, resolve

django.setup()
path = sys.argv[1] if len(sys.argv) > 1 else "/api/v1/auth/token"
try:
    m = resolve(path)
except Resolver404:
    pass
