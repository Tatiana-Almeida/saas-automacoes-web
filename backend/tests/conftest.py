import os
import secrets
import string

import pytest

try:
    from backend.tests.helpers.tenant import create_tenant as _create_tenant
except Exception:
    _create_tenant = None


def pytest_ignore_collect(collection_path):
    """Skip heavy tenant/RBAC tests when running with lightweight SQLite test settings."""
    using_settings_test = os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('settings_test')
    if not using_settings_test:
        return False
    p = str(collection_path)
    skip_patterns = (
        'test_rbac',
        'test_tenant',
        'test_plan_',
        'test_daily_',
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


@pytest.fixture(autouse=True, scope='session')
def enable_db_for_postgres(django_db_blocker):
    """Unblock DB access for the whole session when running Postgres-backed tests.

    This allows middleware (django-tenants) and view tests that rely on DB
    lookups to run without adding `db` to every test.
    """
    # If we're NOT running the lightweight SQLite test settings, allow DB access
    # for the test session (tests expect Postgres + django-tenants middleware).
    if not os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('settings_test'):
        django_db_blocker.unblock()
    yield


@pytest.fixture(autouse=True)
def ensure_public_schema_per_test(request, django_db_blocker):
    """Make sure the connection is set to the public schema at test start."""
    using_settings_test = os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('settings_test')
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
                    helper_path = Path(__file__).resolve().parents[1] / "tests" / "helpers" / "tenant.py"
                    spec = importlib.util.spec_from_file_location("tenant_helper", str(helper_path))
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    _create_tenant = getattr(module, 'create_tenant')
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
    using_settings_test = os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('settings_test')
    if using_settings_test:
        return
    # Request the `transactional_db` fixture so the test runs with transactional
    # DB capabilities (this will create the test DB in a mode that allows
    # schema-level operations during the test lifecycle).
    try:
        request.getfixturevalue('transactional_db')
    except Exception:
        pass


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


@pytest.fixture(autouse=True, scope='session')
def ensure_test_tenant(django_db_setup, django_db_blocker):
    """Create a minimal tenant + domain for hostname `testserver` when using Postgres."""
    with django_db_blocker.unblock():
        try:
            from django.db import connection
            connection.set_schema_to_public()
            from apps.tenants.models import Tenant, Domain
        except Exception:
            return
        if not Domain.objects.filter(domain='testserver').exists():
            tenant = Tenant(schema_name='test_tenant', name='Test Tenant', plan='free')
            tenant.save()
            Domain.objects.create(domain='testserver', tenant=tenant)
    return


@pytest.fixture(autouse=True, scope='session')
def auto_migrate_new_tenants(django_db_blocker):
    """Ensure tenant schemas are migrated when tests create tenants.

    Rationale:
    - Tests commonly create `Tenant` objects at runtime then perform requests
      against tenant-scoped endpoints. Those requests fail if the tenant schema
      does not have migrations applied (ProgrammingError: relation "x" does not exist).
    - We patch `Tenant.save` during the test session so that after a tenant is
      created the test runner runs `migrate_schemas --tenant <schema>` to apply
      tenant migrations in a deterministic, test-only manner.

    Notes / rules followed:
    - This fixture is TEST-ONLY and guarded by the `DJANGO_SETTINGS_MODULE`
      check below so it will not run under lightweight `settings_test`.
    - Exceptions from migration are NOT silenced — failures will surface so
      test suite authors can address missing migrations.
    - The original `Tenant.save` is restored at teardown to avoid leaking the
      patch outside the test run.
    """
    using_settings_test = os.environ.get('DJANGO_SETTINGS_MODULE', '').endswith('settings_test')
    if using_settings_test:
        return

    with django_db_blocker.unblock():
        try:
            from apps.tenants.models import Tenant
            from django.core.management import call_command
        except Exception:
            # If imports fail, do not attempt to patch; let tests continue
            return

        orig_save = Tenant.save

        def save_and_migrate(self, *args, **kwargs):
            # Keep original save behavior and propagate any exceptions
            rv = orig_save(self, *args, **kwargs)
            # Schedule tenant migrations to run after the current DB transaction
            # commits. Running migrations inside an active transaction causes
            # TransactionManagementError; scheduling with `on_commit` ensures
            # migrations execute in a separate transaction after the test
            # transaction finishes.
            try:
                from django.db import transaction
                transaction.on_commit(lambda: call_command('migrate_schemas', tenant=self.schema_name, noinput=True))
            except Exception:
                # If scheduling fails, propagate so tests fail loudly rather
                # than silently continuing with a missing schema.
                raise
            return rv

        Tenant.save = save_and_migrate

    yield

    # Restore original save implementation to avoid side effects beyond tests
    try:
        Tenant.save = orig_save
    except Exception:
        # Avoid masking teardown issues — raise to surface problems
        raise
