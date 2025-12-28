import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saas_backend.settings")
django.setup()

from apps.tenants.models import Domain, Tenant

# Check if public tenant exists
t = Tenant.objects.filter(schema_name="public").first()
if t:
    pass
else:
    t = Tenant.objects.create(schema_name="public", name="Public", plan="free")

# Check if localhost domain exists
d, created = Domain.objects.get_or_create(
    domain="localhost", defaults={"tenant": t, "is_primary": True}
)
if created:
    pass
else:
    pass
