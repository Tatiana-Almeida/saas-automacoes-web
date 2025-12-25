from django.apps import AppConfig


def _ensure_public_domains_for_testing():
    """Best-effort: during tests/dev, ensure a public tenant/domain exists
    so requests with Host 'testserver' don't 404 under django-tenants.
    Safe no-op if tables aren't ready or records already exist.
    """
    import os

    # Only attempt in tests or explicit env
    if not (
        os.environ.get("PYTEST_CURRENT_TEST")
        or os.environ.get("DJANGO_TESTING")
        or os.environ.get("DEBUG") == "True"
    ):
        return
    try:
        from django.db import connection

        # Verify required tables exist before touching ORM
        tables = set(connection.introspection.table_names())
        if not {"tenants_tenant", "tenants_domain"}.issubset(tables):
            return
        from .models import Tenant, Domain

        # Ensure a Tenant row for public exists
        public, _ = Tenant.objects.get_or_create(
            schema_name="public",
            defaults={
                "name": "Public",
                "plan": "free",
                "is_active": True,
            },
        )
        # Map localhost and testserver to public schema for dev/tests
        for host in ("localhost", "testserver"):
            try:
                Domain.objects.get_or_create(
                    domain=host, defaults={"tenant": public, "is_primary": True}
                )
            except Exception:
                # Some versions of DomainMixin may not have is_primary
                Domain.objects.get_or_create(domain=host, defaults={"tenant": public})
    except Exception:
        # Never break app startup due to this helper
        return


class TenantsConfig(AppConfig):
    name = "apps.tenants"
    label = "tenants"

    def ready(self):
        _ensure_public_domains_for_testing()
        # Import tenant signals (seed on create) if available
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
