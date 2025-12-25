import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saas_backend.settings")
django.setup()

from apps.tenants.models import Tenant, Domain

# Check if public tenant exists
t = Tenant.objects.filter(schema_name="public").first()
if t:
    print(f"Public tenant already exists: {t}")
else:
    t = Tenant.objects.create(schema_name="public", name="Public", plan="free")
    print(f"Created tenant: {t}")

# Check if localhost domain exists
d, created = Domain.objects.get_or_create(
    domain="localhost", defaults={"tenant": t, "is_primary": True}
)
if created:
    print(f"Created domain: {d.domain} -> {d.tenant.schema_name}")
else:
    print(f"Domain already exists: {d.domain} -> {d.tenant.schema_name}")
