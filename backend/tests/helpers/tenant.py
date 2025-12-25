"""Test helper for creating tenants in pytest runs.

This module exposes `create_tenant` which is the single supported way for
tests to create tenant schemas. The helper makes schema creation and
migration explicit and deterministic so tests do not observe
ProgrammingError: relation "xxx" does not exist.

Design notes:
- Do not swallow migration errors: if `migrate_schemas` fails we let
  the exception propagate so the test fails loudly.
- The helper is safe to call from tests that have `transactional_db` or
  `django_db` fixtures; it performs operations that require an unblocked
  DB connection and uses Django APIs rather than fragile monkeypatches.
"""

from typing import Optional

from django.core.management import call_command
from django.db import connection

from apps.tenants.models import Tenant, Domain
from apps.core import middleware as core_middleware


def create_tenant(
    schema_name: str = "test_tenant",
    domain: str = "testserver",
    name: Optional[str] = None,
    plan: Optional[str] = "free",
    register_in_process_registry: bool = True,
    **tenant_kwargs,
):
    """Create a Tenant and ensure its schema is present and migrated.

    Steps performed (explicit & deterministic):
    1. Create and save the `Tenant` model instance.
    2. Ensure the tenant schema exists at the DB level.
    3. Ensure the `Domain` mapping exists in the public schema so middleware
       can resolve requests by host during tests.
    4. Run `migrate_schemas --tenant=<schema>` to apply tenant migrations.
    5. (Optional) create lightweight views in the tenant schema that proxy
       certain shared public tables used by tenant-scoped code (idempotent).

    The function raises on errors from Django management commands so tests
    surface migration problems immediately.

    Returns the created `Tenant` instance.
    """

    # Create tenant model instance and save it. Tests should provide any
    # additional model fields via tenant_kwargs.
    tenant = Tenant(
        schema_name=schema_name,
        name=name or schema_name,
        plan=plan,
        **tenant_kwargs,
    )
    tenant.save()

    # All subsequent DB-level operations require an unblocked DB connection.
    # Tests that call this helper must be using `transactional_db` or
    # otherwise allow DB access; if not, pytest/pytest-django will raise.
    # We use raw SQL only to ensure the schema exists; migration command will
    # create tables.
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")

    # Ensure Domain is created in public schema so middleware can resolve host
    # to tenant even if the test's tenant row isn't visible to other DB
    # connections. Use explicit schema switch to public for clarity.
    try:
        connection.set_schema_to_public()
    except Exception:
        # If set_schema_to_public is not available for some DB backend,
        # continue — Domain creation will still be attempted.
        pass

    Domain.objects.get_or_create(domain=domain, defaults={"tenant": tenant})
    # Register common host variant with port to match tests that set HTTP_HOST
    Domain.objects.get_or_create(domain=f"{domain}:80", defaults={"tenant": tenant})

    # Run tenant migrations explicitly. Do not silence exceptions — if this
    # fails the test should fail so migrations are fixed.
    call_command("migrate_schemas", tenant=schema_name, noinput=True)

    # Create simple proxy views in tenant schema for shared public tables
    # used by tenant-scoped code (idempotent). Do not hide errors here but
    # tolerate if the DB backend does not support views.
    with connection.cursor() as cursor:
        cursor.execute(
            f"CREATE OR REPLACE VIEW {schema_name}.auditing_auditlog AS "
            "SELECT * FROM public.auditing_auditlog;"
        )
        cursor.execute(
            f"CREATE OR REPLACE VIEW {schema_name}.auditing_auditretentionpolicy AS "
            "SELECT * FROM public.auditing_auditretentionpolicy;"
        )

    # Register in-process mapping used by request-time middleware so tests
    # using the same Python process can resolve tenants even if DB visibility
    # across connections is limited by pytest transactional behavior.
    if register_in_process_registry:
        core_middleware.TEST_DOMAIN_REGISTRY[domain] = tenant
        core_middleware.TEST_DOMAIN_REGISTRY[f"{domain}:80"] = tenant

    return tenant

