import pytest
from django.test import Client


@pytest.fixture
def tenant_client():
    """
    Factory fixture that returns a Django test `Client` pre-configured
    with the `X-Tenant-Host` header for requests.

    Usage:
        c = tenant_client('tenant1.localhost')
        resp = c.get('/some-url/')
    """

    def _factory(tenant_host: str):
        return Client(HTTP_X_TENANT_HOST=tenant_host)

    return _factory
