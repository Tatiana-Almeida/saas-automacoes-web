import pytest
from django.test import override_settings
from django.http import JsonResponse
from django.urls import path


def echo_view(request):
    return JsonResponse({"tenant_header": request.META.get("HTTP_X_TENANT_HOST")})


urlpatterns = [path("echo/", echo_view, name="echo")]


@pytest.mark.django_db
@override_settings(ROOT_URLCONF=__name__)
def test_tenant_client_sets_header(tenant_client):
    c = tenant_client("tenant1.localhost")
    resp = c.get("/echo/")
    assert resp.status_code == 200
    assert resp.json().get("tenant_header") == "tenant1.localhost"
