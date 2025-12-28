import os
import secrets
import string

import pytest
from django import db


def pytest_ignore_collect(path):
    """
    Skip tenant/RBAC tests when running under the SQLite-based test settings.
    This avoids importing apps that require Postgres/django_tenants in this environment.
    """
    using_settings_test = os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(
        "settings_test"
    )
    if using_settings_test:
        p = str(path)
        patterns = (
            "test_auditing_middleware.py",
            "test_daily_reset.py",
            "test_daily_smoke_summary.py",
            "test_daily_summary.py",
            "test_daily_summary_percent.py",
            "test_daily_summary_threshold.py",
            "test_plan_limits.py",
            "test_plan_limits_services.py",
            "test_plan_ref_override.py",
            "test_rbac.py",
            "test_rbac_audit_actions.py",
            "test_rbac_bulk_api.py",
            "test_rbac_endpoints.py",
            "test_rbac_user_permissions.py",
            "test_reset_daily_counters_command.py",
            "test_service_permissions.py",
            "test_tenant_plan_change.py",
            "test_tenant_plan_detail.py",
            "test_events.py",
        )
        for name in patterns:
            if p.endswith(name):
                return True
    return False


def _random_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@pytest.fixture(scope="session")
def gen_password():
    def _gen() -> str:
        env = os.getenv("TEST_PASSWORD")
        return env if env else _random_password()

    return _gen


@pytest.fixture
def create_tenant(django_db_blocker):
    """Return a callable that creates a tenant while allowing DB access.

    Tests can call the returned function directly: `create_tenant(schema_name=..., ...)`.
    The wrapper unblocks DB access so callers don't need to manage `transactional_db`.
    """

    def _create(**kwargs):
        with django_db_blocker.unblock():
            try:
                from tests.utils.tenants import create_tenant as _helper
            except Exception:
                from backend.tests.helpers.tenant import create_tenant as _helper
            return _helper(**kwargs)

    return _create


def pytest_collection_modifyitems(config, items):
    """Skip tenant/RBAC-dependent tests when running under SQLite test settings.

    These tests rely on django-tenants/Postgres features and won't run under the
    minimal SQLite-based test configuration used for focused unit testing.
    """
    try:
        from django.conf import settings

        engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    except Exception:
        engine = ""
    if "sqlite" in engine:
        skip = pytest.mark.skip(
            reason="Skipped under SQLite test settings; requires Postgres tenants backend"
        )
        patterns = (
            "test_auditing_middleware.py",
            "test_daily_",
            "test_plan_",
            "test_rbac",
            "test_reset_daily_counters_command.py",
            "test_service_permissions.py",
            "test_tenant_",
        )
        for item in items:
            fspath = str(getattr(item, "fspath", ""))
            if any(p in fspath for p in patterns):
                item.add_marker(skip)


# Enable DB for tests that use the Django `client` fixture.
@pytest.fixture(autouse=True)
def _enable_db_for_client(request):
    if "client" in getattr(request, "fixturenames", []):
        request.getfixturevalue("db")


# Ensure each test begins with the public schema active.
@pytest.fixture(autouse=True)
def _ensure_public_schema_per_test(request, django_db_blocker):
    using_settings_test = os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(
        "settings_test"
    )
    if using_settings_test:
        return
    with django_db_blocker.unblock():
        try:
            from django.db import connection

            connection.set_schema_to_public()
        except Exception:
            pass


# Clear Django cache (Redis) before and after each test to isolate state.
@pytest.fixture(autouse=True)
def _clear_cache_between_tests():
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


@pytest.fixture(autouse=True)
def _flush_redis_between_tests():
    """If Django is configured to use Redis for caching/broker, flush the test DB
    before and after each test to avoid residual state leaking between tests.

    Safety:
    - Does nothing if cache backend is not Redis.
    - Avoids flushing DB index 0 unless explicitly allowed via env `ALLOW_FLUSH_REDIS_DB0`.
    """
    try:
        import os

        from django.conf import settings

        # Resolve candidate Redis URL from common settings
        url = None
        # First prefer cache LOCATION when Redis backend is in use
        caches = getattr(settings, "CACHES", {}) or {}
        default_cache = caches.get("default", {})
        backend = default_cache.get("BACKEND", "")
        if "RedisCache" in backend:
            url = default_cache.get("LOCATION")

        # Fallback to common broker/result backend
        if not url:
            url = getattr(settings, "CELERY_BROKER_URL", None) or os.environ.get(
                "REDIS_URL"
            )

        if not url:
            # Nothing to do
            yield
            return

        # Parse DB index from URL (redis://host:port/db)
        import re

        m = re.search(r"/(\d+)(?:\?|$)", url)
        db_index = int(m.group(1)) if m else None

        # Safety guard: avoid accidentally flushing DB 0 unless explicitly allowed
        allow_db0 = os.environ.get("ALLOW_FLUSH_REDIS_DB0", "0") == "1"
        if db_index is None:
            # If unspecified, default to DB 0 — skip unless allowed
            if not allow_db0:
                yield
                return

        if db_index == 0 and not allow_db0:
            yield
            return

        # Connect and flush
        try:
            import redis

            r = redis.from_url(url, decode_responses=False)
            try:
                r.flushdb()
            except Exception:
                pass
        except Exception:
            # If redis client not available or connection fails, skip silently
            yield
            return
    except Exception:
        yield
        return

    yield

    try:
        # Post-test cleanup
        import redis

        r = redis.from_url(url, decode_responses=False)
        try:
            r.flushdb()
        except Exception:
            pass
    except Exception:
        pass


@pytest.fixture(autouse=True, scope="session")
def _ensure_test_tenant(django_db_setup, django_db_blocker):
    """Create a lightweight tenant + domain for the testserver hostname.

    Ensures `testserver` domain resolves during tests that use Django test client.
    """
    with django_db_blocker.unblock():
        try:
            from apps.tenants.models import Domain, Tenant
            from django.db import connection

            connection.set_schema_to_public()
        except Exception:
            return
        if not Domain.objects.filter(domain="testserver").exists():
            tenant = Tenant(schema_name="test_tenant", name="Test Tenant", plan="free")
            tenant.save()
            Domain.objects.create(domain="testserver", tenant=tenant)
    return


@pytest.fixture(autouse=True, scope="session")
def _disable_throttles_session():
    """Ensure DRF throttle classes are disabled for the test session unless a test
    explicitly sets them. This avoids intermittent 429s during high-concurrency tests.
    """
    try:
        from django.conf import settings

        rf = getattr(settings, "REST_FRAMEWORK", None)
        if isinstance(rf, dict):
            rf["DEFAULT_THROTTLE_CLASSES"] = ()
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True)
def close_db_connections_after_test():
    """Close Django DB connections after each test to avoid lingering sessions."""
    yield
    try:
        db.connections.close_all()
    except Exception:
        pass


@pytest.fixture(autouse=True, scope="session")
def _ensure_test_tenant_general(django_db_setup, django_db_blocker):
    using_settings_test = os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(
        "settings_test"
    )
    if using_settings_test:
        return


@pytest.fixture(scope="session", autouse=True)
def _ensure_shared_migrations_applied(django_db_setup, django_db_blocker):
    """Ensure shared/public schema migrations are applied to the test database.

    Pytest-django creates a fresh test database which does not run django-tenants
    shared migrations automatically. Apply `migrate` and `migrate_schemas --shared`
    once per test session so ORM queries (e.g. `Tenant.objects`) succeed.
    """
    using_settings_test = os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(
        "settings_test"
    )
    if using_settings_test:
        return
    with django_db_blocker.unblock():
        try:
            import time

            from django import db as django_db
            from django.core.management import call_command

            # Ensure standard app migrations are applied
            call_command("migrate", verbosity=0, interactive=False)
            # Ensure django-tenants shared/public schema migrations are applied
            call_command("migrate_schemas", shared=True, noinput=True, verbosity=0)

            # Signal to tenant helper that shared migrations are ready so
            # concurrent tenant-creation threads can proceed safely.
            try:
                import importlib

                tenant_mod = importlib.import_module("tests.helpers.tenant")
                ev = getattr(tenant_mod, "MIGRATIONS_READY", None)
                if ev is None:
                    # Create the event if it doesn't exist yet on the module.
                    import threading

                    tenant_mod.MIGRATIONS_READY = threading.Event()
                    ev = tenant_mod.MIGRATIONS_READY
                try:
                    ev.set()
                except Exception:
                    pass
            except Exception:
                pass

            # Close all DB connections so other threads/processes see the
            # newly created tables immediately. Small sleep ensures the
            # postgres server has time to make the changes visible.
            try:
                django_db.connections.close_all()
            except Exception:
                pass
            time.sleep(0.1)
        except Exception:
            # If migrations fail here, raise so CI/tests fail loudly.
            raise
    with django_db_blocker.unblock():
        try:
            from apps.tenants.models import Domain, Tenant
            from django.db import connection

            connection.set_schema_to_public()
        except Exception:
            return
        if not Domain.objects.filter(domain="testserver").exists():
            tenant = Tenant(schema_name="test_tenant", name="Test Tenant", plan="free")
            tenant.save()
            Domain.objects.create(domain="testserver", tenant=tenant)
        return
