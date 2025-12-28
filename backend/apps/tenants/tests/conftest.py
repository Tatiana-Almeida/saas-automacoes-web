import pytest
from django.test import Client


@pytest.fixture
def tenant_client():
    """Provide a factory that returns a Django test Client with the
    `X-Tenant-Host` header set for requests.
    """

    def _factory(tenant_host: str):
        return Client(HTTP_X_TENANT_HOST=tenant_host)

    return _factory
