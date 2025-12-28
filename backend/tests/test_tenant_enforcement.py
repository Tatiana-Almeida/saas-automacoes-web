import pytest
from apps.core.middleware import EnforceActiveTenantMiddleware
from django.http import JsonResponse
from django.test import RequestFactory


class DummyTenant:
    def __init__(self, is_active=True):
        self.is_active = is_active
        self.id = 123
        self.schema_name = "dummy"


def dummy_view(_request):
    return JsonResponse({"ok": True}, status=200)


@pytest.mark.django_db
def test_enforce_active_tenant_blocks_suspended():
    rf = RequestFactory()
    req = rf.get("/any")
    req.tenant = DummyTenant(is_active=False)

    mw = EnforceActiveTenantMiddleware(dummy_view)
    resp = mw(req)
    assert resp.status_code == 403
    # Ensure payload contains message
    # Note: resp.content is bytes; we check substring
    assert b"Tenant suspenso" in resp.content


@pytest.mark.django_db
def test_enforce_active_tenant_allows_active():
    rf = RequestFactory()
    req = rf.get("/any")
    req.tenant = DummyTenant(is_active=True)

    mw = EnforceActiveTenantMiddleware(dummy_view)
    resp = mw(req)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_enforce_active_tenant_allows_no_tenant():
    rf = RequestFactory()
    req = rf.get("/any")

    mw = EnforceActiveTenantMiddleware(dummy_view)
    resp = mw(req)
    assert resp.status_code == 200
