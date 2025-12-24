from django.core.management import call_command
from django.db import connection

from apps.tenants.models import Tenant, Domain
from apps.core import middleware as core_middleware


def create_tenant(schema_name: str = "test_tenant", domain: str = "testserver", **tenant_kwargs):
    """Create a tenant and ensure its schema is migrated.

    Returns the Tenant instance. Ensures the tenant schema exists and runs
    `migrate_schemas --tenant <schema>` so tests can use tenant-scoped tables.
    """
    tenant = Tenant(schema_name=schema_name, **tenant_kwargs)
    tenant.save()

    with connection.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS %s" % schema_name)

    # Ensure the Domain exists in public schema before running tenant migrations
    # so middleware that resolves tenants by host can find it during requests.
    try:
        connection.set_schema_to_public()
    except Exception:
        pass
    Domain.objects.get_or_create(domain=domain, defaults={"tenant": tenant})
    # Also register common host variants (with explicit port) to match HTTP_HOST values
    try:
        Domain.objects.get_or_create(domain=f"{domain}:80", defaults={"tenant": tenant})
    except Exception:
        pass

    call_command("migrate_schemas", tenant=schema_name, noinput=True)

    # Create lightweight views in the tenant schema that point to shared
    # auditing tables in `public`. Some code writes/reads audit logs while the
    # DB search_path is set to the tenant schema only; creating these views
    # lets tenant-scoped queries access the central audit tables.
    with connection.cursor() as cursor:
        # Ensure view creation is idempotent
        try:
            cursor.execute(
                "CREATE OR REPLACE VIEW %s.auditing_auditlog AS SELECT * FROM public.auditing_auditlog;" % schema_name
            )
        except Exception:
            # Not critical; ignore if DB doesn't support views in this config
            pass
        try:
            cursor.execute(
                "CREATE OR REPLACE VIEW %s.auditing_auditretentionpolicy AS SELECT * FROM public.auditing_auditretentionpolicy;" % schema_name
            )
        except Exception:
            pass

    # Final ensure for idempotency
    try:
        Domain.objects.get_or_create(domain=domain, defaults={"tenant": tenant})
        try:
            import logging
            logger = logging.getLogger('apps.tests')
            vals = list(Domain.objects.filter(domain__icontains=domain).values_list('domain', flat=True))
            logger.info('create_tenant registered domains for %s: %s', domain, vals)
        except Exception:
            pass
    except Exception:
        pass

    # Also register in-process mapping so test request-time middleware
    # can resolve the tenant even if the DB row is not visible to other
    # DB connections (common in pytest transactional tests).
    try:
        core_middleware.TEST_DOMAIN_REGISTRY[domain] = tenant
        core_middleware.TEST_DOMAIN_REGISTRY[f"{domain}:80"] = tenant
    except Exception:
        pass

    return tenant
