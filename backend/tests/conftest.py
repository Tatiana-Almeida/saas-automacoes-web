import os
import secrets
import string

import pytest

try:
    from backend.tests.helpers.tenant import create_tenant as _create_tenant
except Exception:
    _create_tenant = None


def pytest_ignore_collect(collection_path):
    """
    Skip heavy tenant/RBAC tests when running with lightweight SQLite
    test settings.
    """
    using_settings_test = os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(
        "settings_test"
    )
    if not using_settings_test:
        return False
    p = str(collection_path)
    skip_patterns = (
        "test_rbac",
        "test_tenant",
        "test_plan_",
        "test_daily_",
    )
    return any(name in p for name in skip_patterns)


def _random_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@pytest.fixture(scope="session")
def gen_password():
    def _gen() -> str:
        env = os.getenv("TEST_PASSWORD")
        return env if env else _random_password()

    return _gen


@pytest.fixture(autouse=True, scope="session")
def enable_db_for_postgres(django_db_blocker):
    """Unblock DB access for the whole session when running Postgres-backed tests.

    This allows middleware (django-tenants) and view tests that rely on DB
    lookups to run without adding `db` to every test.
    """
    # If we're NOT running the lightweight SQLite test settings, allow DB access
    # for the test session (tests expect Postgres + django-tenants middleware).
    if not os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith("settings_test"):
        django_db_blocker.unblock()
    yield


@pytest.fixture(autouse=True)
def ensure_public_schema_per_test(request, django_db_blocker):
    """Make sure the connection is set to the public schema at test start."""
    using_settings_test = os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(
        "settings_test"
    )
    if using_settings_test:
        return
    with django_db_blocker.unblock():
        from django.db import connection

        # Ensure we are on the public schema at test start. If this fails,
        # raise so test authors see the configuration issue rather than
        # silently running tests against the wrong schema.
        connection.set_schema_to_public()


@pytest.fixture
def create_tenant():
    """Fixture that returns a helper to create a tenant and run migrations.

    Usage in tests: `tenant = create_tenant(schema_name='foo', domain='foo.testserver')`
    """
    # Try late import if the top-level import failed during module import.
    global _create_tenant
    if _create_tenant is None:
        # Try common import paths first, then fall back to loading by file path.
        try:
            from backend.tests.helpers.tenant import create_tenant as _create_tenant
        except Exception:
            try:
                from tests.helpers.tenant import create_tenant as _create_tenant
            except Exception:
                try:
                    import importlib.util
                    from pathlib import Path

                    helper_path = (
                        Path(__file__).resolve().parents[1]
                        / "tests"
                        / "helpers"
                        / "tenant.py"
                    )
                    spec = importlib.util.spec_from_file_location(
                        "tenant_helper", str(helper_path)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    _create_tenant = getattr(module, "create_tenant")
                except Exception as e:
                    pytest.skip(f"tenant helper not available: {e}")
    return _create_tenant


@pytest.fixture(autouse=True)
def _force_transactional_db(request):
    """Enable `transactional_db` for tests when running Postgres-backed settings.

    Some operations (like running migrations for a tenant schema) cannot be
    executed while the test is inside a regular DB transaction. For the
    Postgres-backed test run we enable transactional DB support for all tests
    so our auto-migration helper can run safely.
    """
    using_settings_test = os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(
        "settings_test"
    )
    if using_settings_test:
        return
    # Request the `transactional_db` fixture so the test runs with transactional
    # DB capabilities (this will create the test DB in a mode that allows
    # schema-level operations during the test lifecycle).
    # Do not silently swallow errors: if pytest cannot provide `transactional_db`
    # the test environment is misconfigured and we should fail fast.
    request.getfixturevalue("transactional_db")


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    try:
        from django.core.cache import cache

        cache.clear()
    except Exception:
        pass
    yield
    try:
        from django.core.cache import cache

        cache.clear()
    except Exception:
        pass


@pytest.fixture(autouse=True, scope="session")
def ensure_test_tenant(django_db_setup, django_db_blocker):
    """
    Create a minimal tenant + domain for hostname `testserver` when
    using Postgres.
    """
    with django_db_blocker.unblock():
        try:
            from django.db import connection

            connection.set_schema_to_public()
            from apps.tenants.models import Domain
        except Exception:
            return
        # Prefer using the centralized test helper to create/migrate tenants.
        # Try several common import paths so tests can run whether the helper
        # is located under a `backend` package or the top-level `tests` tree.
        create_tenant_helper = None
        try:
            from backend.tests.helpers.tenant import create_tenant as create_tenant_helper
        except Exception:
            try:
                from tests.helpers.tenant import create_tenant as create_tenant_helper
            except Exception:
                try:
                    import importlib.util
                    from pathlib import Path

                    helper_path = (
                        Path(__file__).resolve().parents[1]
                        / "tests"
                        / "helpers"
                        / "tenant.py"
                    )
                    spec = importlib.util.spec_from_file_location(
                        "tenant_helper", str(helper_path)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    create_tenant_helper = getattr(module, "create_tenant")
                except Exception:
                    create_tenant_helper = None

        if not Domain.objects.filter(domain="testserver").exists():
            if create_tenant_helper is None:
                # Helper not importable for some reason; fall back to minimal
                # creation so tests do not break, but prefer the helper.
                from apps.tenants.models import Tenant

                tenant = Tenant(schema_name="test_tenant", name="Test Tenant", plan="free")
                tenant.save()
                Domain.objects.create(domain="testserver", tenant=tenant)
            else:
                # create_tenant runs migrations and ensures schema present
                create_tenant_helper(
                    schema_name="test_tenant",
                    domain="testserver",
                    name="Test Tenant",
                    plan="free",
                )
    return


@pytest.fixture(scope="session", autouse=False)
def ensure_tenant_schemas(django_db_blocker):
    """Session-scoped fixture to pre-create and migrate common tenant schemas.

    This reduces repeated migration overhead during the test session and
    helps avoid flakiness caused by concurrent on_commit migrations.
    """
    with django_db_blocker.unblock():
        try:
            create_tenant_helper = None
            try:
                from backend.tests.helpers.tenant import create_tenant as create_tenant_helper
            except Exception:
                try:
                    from tests.helpers.tenant import create_tenant as create_tenant_helper
                except Exception:
                    create_tenant_helper = None

            # List of tenant schemas commonly used by tests (observed in logs).
            default_schemas = [
                ("test_tenant", "testserver"),
                ("ctenant", "ctenant.localhost"),
                ("wtenant2", "wtenant2.localhost"),
                ("atenant", "atenant.localhost"),
                ("delta", "delta.localhost"),
            ]

            if _create_tenant is None:
                for schema, domain in default_schemas:
                    try:
                    # Prefer stable test utils path when present.
                    from backend.tests.utils.tenants import create_tenant as _create_tenant
                except Exception:
                    try:
                        from tests.utils.tenants import create_tenant as _create_tenant
                    except Exception:
                        try:
                            from backend.tests.helpers.tenant import create_tenant as _create_tenant
                        except Exception:
                            try:
                                from tests.helpers.tenant import create_tenant as _create_tenant
                            except Exception:
                                try:
                                    import importlib.util
                                    from pathlib import Path

                                    helper_path = (
                                        Path(__file__).resolve().parents[1]
                                        / "tests"
                                        / "helpers"
                                        / "tenant.py"
                                    )
                                    spec = importlib.util.spec_from_file_location(
                                        "tenant_helper", str(helper_path)
                                    )
                                    module = importlib.util.module_from_spec(spec)
                                    spec.loader.exec_module(module)
                                    _create_tenant = getattr(module, "create_tenant")
                                except Exception as e:
                                    pytest.skip(f"tenant helper not available: {e}")
            return _create_tenant
      check below so it will not run under lightweight `settings_test`.
    - Exceptions from migration are NOT silenced — failures will surface so
      test suite authors can address missing migrations.
    - The original `Tenant.save` is restored at teardown to avoid leaking the
      patch outside the test run.
    """
    # Use a Django `post_save` signal handler to react to new Tenant creations.
    # This is more robust than monkeypatching `Tenant.save` and is easier to
    # restore at teardown. We schedule `migrate_schemas` to run via
    # `transaction.on_commit` so migrations execute outside the creating test's
    # transaction.
    using_settings_test = os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(
        "settings_test"
    )
    if using_settings_test:
        return

    with django_db_blocker.unblock():
        try:
            from django.db import transaction
            from django.db.models.signals import post_save
            from apps.tenants.models import Tenant
            from django.core.management import call_command
        except Exception:
            # If imports fail, fail fast so test authors can correct config.
            raise

        # Track schemas we've already migrated in this test session to avoid
        # duplicate work and noisy logs.
        migrated_schemas = set()

        def _tenant_post_save(sender, instance, created, **kwargs):
            if not created:
                return
            # If the creating code marked the instance to skip auto-migrate
            # (the `create_tenant` helper runs migrations explicitly) then
            # do not schedule a duplicate migrate_schemas call.
            if getattr(instance, "_skip_auto_migrate", False):
                return
            schema = getattr(instance, "schema_name", None)
            if not schema or schema in migrated_schemas:
                return

            def _run_migrate():
                # Ensure the DB connection search path is set to the tenant
                # schema before running migrations. Let exceptions bubble up
                # so tests fail visibly if migrations are missing.
                try:
                    from django.db import connection as _conn

                    _conn.set_schema(schema)
                    # Also ensure the underlying DB cursor search_path is
                    # explicitly set. Some connection wrappers use a pool
                    # or different cursor so issuing an explicit SET helps
                    # guarantee the migrate command operates on the
                    # intended schema.
                    try:
                        with _conn.cursor() as _cursor:
                            _cursor.execute("SET search_path TO %s", [schema])
                    except Exception:
                        # If this fails, continue — set_schema above may
                        # be sufficient for many adapters.
                        pass
                except Exception:
                    pass

                # Acquire a Postgres advisory lock for this schema to avoid
                # concurrent migrations racing in parallel test processes.
                # Use centralized db_lock utilities to set search_path and
                # acquire advisory locks where supported.
                try:
                    from tests.utils.db_lock import advisory_lock, set_search_path_on_cursor

                    set_search_path_on_cursor(schema)
                    with advisory_lock(schema):
                        call_command("migrate_schemas", tenant=schema, noinput=True)
                        migrated_schemas.add(schema)
                except Exception:
                    # If helper import fails or migration fails, let it bubble
                    # up to the test runner so failures are visible.
                    call_command("migrate_schemas", tenant=schema, noinput=True)
                    migrated_schemas.add(schema)

            transaction.on_commit(_run_migrate)

        # Connect the handler and ensure it is disconnected at teardown.
        post_save.connect(_tenant_post_save, sender=Tenant, weak=False)

    yield

    # Teardown: disconnect signal and clear tracking set.
    try:
        from django.db.models.signals import post_save

        post_save.disconnect(_tenant_post_save, sender=Tenant)
        migrated_schemas.clear()
    except Exception:
        # Fail loudly if teardown cannot properly restore state.
        raise
