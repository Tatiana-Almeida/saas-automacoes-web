from typing import Optional

from django.conf import settings


def create_tenant(schema_name: str, domain: str, name: Optional[str] = None, plan: str = "free"):
    """Create a tenant (runtime helper).

    - In normal (Postgres) deployments this will save the Tenant model which
      triggers schema creation (django-tenants `auto_create_schema`). It will
      also create the Domain mapping and attempt to run tenant migrations via
      the management command `migrate_schemas --tenant=<schema>`.

    - In `settings.TESTING` (SQLite test mode) this helper will create the
      Tenant and Domain via the ORM without attempting DB-level schema ops.
    """
    from django.core.management import call_command
    from django.db import connection

    from .models import Domain, Tenant

    # If running tests with SQLite, avoid schema operations; create ORM rows.
    if getattr(settings, "TESTING", False) or connection.vendor == "sqlite":
        tenant, created = Tenant.objects.get_or_create(
            schema_name=schema_name, defaults={"name": name or schema_name, "plan": plan}
        )
        Domain.objects.get_or_create(domain=domain, defaults={"tenant": tenant})
        return tenant

    # Production/Postgres flow: create tenant and ensure schema
    tenant, created = Tenant.objects.get_or_create(
        schema_name=schema_name, defaults={"name": name or schema_name, "plan": plan}
    )
    Domain.objects.get_or_create(domain=domain, defaults={"tenant": tenant})

    try:
        # Ensure schema exists by saving the tenant (django-tenants will create schema)
        if created:
            tenant.save()
        # Run tenant migrations explicitly
        call_command("migrate_schemas", tenant=schema_name, noinput=True)
    except Exception:
        # Surface errors to the caller for operational visibility
        raise

    return tenant
