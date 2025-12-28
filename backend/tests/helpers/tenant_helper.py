

def get_or_create_test_tenant():
    """Create or return a lightweight test Tenant for test runs.

    This lives under `backend/tests/helpers` so application code does not
    accidentally depend on test utilities in production. App-level callers
    should only import this when `settings.TESTING` is True.
    """
    try:
        from django.conf import settings
    except Exception:
        return None

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
