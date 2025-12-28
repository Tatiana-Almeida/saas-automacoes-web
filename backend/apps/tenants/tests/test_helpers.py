import pytest


@pytest.mark.django_db
def test_create_tenant_helper(client, settings):
    """Ensure `create_tenant` creates Tenant and Domain in testing mode."""
    settings.TESTING = True

    from apps.tenants.helpers import create_tenant
    from apps.tenants.models import Tenant, Domain

    schema = "test_create_helper"
    domain = "test_create_helper.local"

    tenant = create_tenant(schema_name=schema, domain=domain, name="Test Helper")

    assert isinstance(tenant, Tenant)
    # Domain should exist and map to tenant
    d = Domain.objects.filter(domain=domain).first()
    assert d is not None
    assert d.tenant.schema_name == schema
