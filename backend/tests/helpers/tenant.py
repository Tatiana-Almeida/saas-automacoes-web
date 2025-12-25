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
import logging
import time
import threading

from tests.utils.db_lock import advisory_lock, set_search_path_on_cursor

# Event set by the session fixture when shared/public migrations have been applied.
MIGRATIONS_READY = threading.Event()

from django.core.management import call_command
import logging
import time

from django.db import connection, connections, transaction

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

    # Wait for shared/public migrations applied by the test session fixture.
    # This avoids races where concurrent test threads attempt to create tenants
    # before the public `tenants_tenant` table exists.
    try:
        MIGRATIONS_READY.wait(timeout=30)
    except Exception:
        pass

    # Serialize tenant creation + schema migration to avoid races when tests
    # create the same tenant concurrently. Acquire an advisory lock keyed
    # by the schema name for the duration of creation/migration.
    with advisory_lock(schema_name):
        # Ensure we're operating against the public schema for tenant model
        # queries and creation.
        try:
            connection.set_schema_to_public()
        except Exception:
            pass

        # Wait briefly for the public tenants table to exist. In pytest's
        # test DB setup there can be a small window where the test database
        # has been created but migrations haven't finished on other threads
        # yet; wait up to ~5s before proceeding to avoid racey calls that
        # result in ``relation "tenants_tenant" does not exist``.
        def _public_table_exists():
            try:
                with connection.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
                        [Tenant._meta.db_table],
                    )
                    return cur.fetchone() is not None
            except Exception:
                return False

        total_wait = 0.0
        # Increase the wait window and use modest sleeps to give pytest's
        # session fixture time to apply migrations in concurrent setups.
        while not _public_table_exists() and total_wait < 10.0:
            time.sleep(0.1)
            total_wait += 0.1

        # Ensure the public tenants table exists before proceeding. In some
        # concurrent test setups the public migrations may not have finished
        # on other threads/processes yet; run public migrations here while
        # holding the advisory lock as a best-effort to avoid `relation
        # "tenants_tenant" does not exist` errors.
        try:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
                    [Tenant._meta.db_table],
                )
                exists = cur.fetchone() is not None
        except Exception:
            exists = False

        if not exists:
            # Bootstrapping: ensure standard app migrations and the
            # django-tenants shared/public migrations are applied while
            # holding the advisory lock. Fail loudly if these commands
            # cannot complete so tests surface the real problem instead
            # of later ``relation ... does not exist`` errors.
            try:
                call_command("migrate", verbosity=0, interactive=False)
                call_command(
                    "migrate_schemas", shared=True, noinput=True, verbosity=0
                )
            except Exception:
                # Re-raise so calling tests see the underlying migration
                # failure rather than a later obscure ProgrammingError.
                raise

        # If another process already created the tenant, return it.
        try:
            existing = Tenant.objects.filter(schema_name=schema_name).first()
            if existing:
                return existing
        except Exception:
            existing = None

        # Insert tenant row directly into the public tenants table to avoid
        # Django-tenants' automatic `create_schema` behavior on `save()`.
        # This gives us explicit control over schema creation and migrations.
        table = Tenant._meta.db_table
        plan_ref_id = None
        if "plan_ref" in tenant_kwargs:
            pr = tenant_kwargs.get("plan_ref")
            try:
                plan_ref_id = pr.id
            except Exception:
                plan_ref_id = pr

        with transaction.atomic():
            try:
                connection.set_schema_to_public()
            except Exception:
                pass

            with connection.cursor() as cursor:
                insert_sql = (
                    f"INSERT INTO public.{table} (schema_name, name, plan, is_active, plan_ref_id, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, now()) RETURNING id"
                )
                cursor.execute(
                    insert_sql,
                    [schema_name, name or schema_name, plan, True, plan_ref_id],
                )
                row = cursor.fetchone()
                tenant_id = row[0] if row else None

        # Load the instance via ORM (no save) so callers get a Tenant object.
        tenant = None
        if tenant_id:
            try:
                connection.set_schema_to_public()
            except Exception:
                pass
            tenant = Tenant.objects.get(pk=tenant_id)

        # Ensure schema exists at DB level while holding the lock.
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

    # Run tenant migrations explicitly while holding the advisory lock to
    # avoid concurrent migrate runs. Re-acquire the advisory_lock here to
    # ensure serialization even if the earlier creation phase released it.
    with advisory_lock(schema_name):
        try:
            # Prefer connection-level schema switch for django-tenants-aware
            # adapters; fall back to cursor-level SET as a safety net.
            try:
                connection.set_schema(schema_name)
            except Exception:
                with connection.cursor() as _cursor:
                    _cursor.execute("SET search_path TO %s", [schema_name])

            set_search_path_on_cursor(schema_name)

            # Retry migrations a small number of times if a race causes
            # MigrationSchemaMissing or transient DB cursor issues.
            attempts = 6
            for attempt in range(1, attempts + 1):
                try:
                    # Preferred: call django-tenants' migration executor API
                    # directly to avoid the management command path that may
                    # query `tenants_tenant` implicitly. We attempt to import
                    # the executor module and find a class exposing
                    # `run_migrations(tenants=...)`. This is resilient to
                    # django-tenants versions that change class names.
                    tried_executor = False
                    try:
                        mod = __import__(
                            "django_tenants.migration_executors.standard",
                            fromlist=["*"],
                        )
                        ExecutorClass = None
                        for name in dir(mod):
                            obj = getattr(mod, name)
                            if isinstance(obj, type) and hasattr(obj, "run_migrations"):
                                ExecutorClass = obj
                                break
                        if ExecutorClass is not None:
                            executor = ExecutorClass()
                            # Some implementations expect a list, others a
                            # single tenant name. Try both.
                            try:
                                executor.run_migrations(tenants=[schema_name])
                            except TypeError:
                                executor.run_migrations(tenants=schema_name)
                            tried_executor = True
                    except Exception:
                        tried_executor = False

                    if not tried_executor:
                        # Fallback to management command when direct API is
                        # unavailable.
                        call_command(
                            "migrate_schemas",
                            tenant=schema_name,
                            noinput=True,
                            verbosity=0,
                        )
                    break
                except Exception:
                    # If final attempt, re-raise; otherwise sleep briefly and retry.
                    if attempt == attempts:
                        raise
                    time.sleep(0.2 * attempt)
        finally:
            # Restore public schema on the connection to avoid leaking tenant
            # search_path into other test code.
            try:
                connection.set_schema_to_public()
            except Exception:
                pass

    # Diagnostics: log current schema/search_path before running migrations.
    try:
        logger = logging.getLogger(__name__)
        with connection.cursor() as cursor:
            try:
                cursor.execute("SELECT current_schema()")
                current = cursor.fetchone()
                logger.debug("pre-migrate current_schema: %r", current)
            except Exception:
                logger.debug("pre-migrate: unable to fetch current_schema")
            try:
                cursor.execute("SHOW search_path")
                sp = cursor.fetchone()
                logger.debug("pre-migrate search_path: %r", sp)
            except Exception:
                logger.debug("pre-migrate: unable to fetch search_path")
            # Ensure search_path is set on the cursor as a safety measure.
            try:
                cursor.execute("SET search_path TO %s", [schema_name])
            except Exception:
                logger.debug("pre-migrate: SET search_path failed")
    except Exception:
        # Continue even if diagnostics fail; we don't want to block tests
        # due to logging/diagnostic issues.
        pass

    # migrations already applied above while holding advisory lock

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

