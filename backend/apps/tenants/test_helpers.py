

def get_or_create_test_tenant():
    """Return an existing Tenant or create a lightweight test Tenant.

    This helper is intended for test-only fallbacks and should only be
    invoked when `settings.TESTING` is True. It avoids duplicating the
    same defensive creation logic across models and keeps behavior
    centralized.
    """
    from django.conf import settings

    # Prefer test helper in `backend.tests.helpers` when available so test
    # utilities live under the tests package. Fall back to an internal
    # minimal implementation if the tests helper cannot be imported.
    try:
        from backend.tests.helpers.tenant_helper import get_or_create_test_tenant as _th

        return _th()
    except Exception:
        pass

    if not getattr(settings, "TESTING", False):
        return None

    try:
        from django.apps import apps as django_apps

        Tenant = django_apps.get_model("tenants", "Tenant")
        Domain = django_apps.get_model("tenants", "Domain")
    except Exception:
        return None

    t = Tenant.objects.first()
    if not t:
        t = Tenant.objects.create(
            name="test_tenant", schema_name="test_tenant", plan="free"
        )
        try:
            Domain.objects.create(domain="testserver", tenant=t)
        except Exception:
            pass
    return t
