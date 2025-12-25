import json
import pytest
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant, Domain

# `create_tenant` fixture is provided via `backend/tests/conftest.py`
from apps.rbac.models import Permission, UserPermission

User = get_user_model()


@pytest.mark.django_db
def test_whatsapp_send_requires_permission(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="wtenant", domain="wtenant.localhost", name="WTenant", plan="pro"
    )
    d = Domain.objects.get(domain="wtenant.localhost")

    pw = gen_password()
    user = User.objects.create_user(username="wuser", password=pw)
    p_send = Permission.objects.create(code="send_whatsapp")

    # Login
    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "wuser", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # Without permission → 403
    r_forbidden = client.post(
        "/api/v1/whatsapp/messages/send",
        data=json.dumps({"to": "+351900000000", "message": "Olá!"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_forbidden.status_code == 403

    # Grant permission and retry → 201
    UserPermission.objects.create(user=user, permission=p_send, tenant=t)
    r_allowed = client.post(
        "/api/v1/whatsapp/messages/send",
        data=json.dumps({"to": "+351900000001", "message": "Perm ok"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_allowed.status_code == 201


@pytest.mark.django_db
def test_email_send_requires_permission(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="etenant", domain="etenant.localhost", name="ETenant", plan="pro"
    )
    d = Domain.objects.get(domain="etenant.localhost")

    pw = gen_password()
    user = User.objects.create_user(username="euser", password=pw)
    p_send = Permission.objects.create(code="email_send")

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "euser", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    r_forbidden = client.post(
        "/api/v1/email/messages/send",
        data=json.dumps({"to": "a@b.com", "subject": "t", "body": "b"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_forbidden.status_code == 403

    UserPermission.objects.create(user=user, permission=p_send, tenant=t)
    r_allowed = client.post(
        "/api/v1/email/messages/send",
        data=json.dumps({"to": "c@d.com", "subject": "t2", "body": "b2"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_allowed.status_code == 201


@pytest.mark.django_db
def test_sms_send_requires_permission(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="stenant", domain="stenant.localhost", name="STenant", plan="pro"
    )
    d = Domain.objects.get(domain="stenant.localhost")

    pw = gen_password()
    user = User.objects.create_user(username="suser", password=pw)
    p_send = Permission.objects.create(code="sms_send")

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "suser", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    r_forbidden = client.post(
        "/api/v1/sms/messages/send",
        data=json.dumps({"to": "+351900000002", "message": "x"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_forbidden.status_code == 403

    UserPermission.objects.create(user=user, permission=p_send, tenant=t)
    r_allowed = client.post(
        "/api/v1/sms/messages/send",
        data=json.dumps({"to": "+351900000003", "message": "y"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_allowed.status_code == 201


@pytest.mark.django_db
def test_chatbots_send_requires_permission(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="ctenant", domain="ctenant.localhost", name="CTenant", plan="pro"
    )
    d = Domain.objects.get(domain="ctenant.localhost")

    pw = gen_password()
    user = User.objects.create_user(username="cuser", password=pw)
    p_send = Permission.objects.create(code="chatbots_send")

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "cuser", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    r_forbidden = client.post(
        "/api/v1/chatbots/messages/send",
        data=json.dumps({"bot_id": "b1", "message": "oi", "session_id": "sess"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_forbidden.status_code == 403

    UserPermission.objects.create(user=user, permission=p_send, tenant=t)
    r_allowed = client.post(
        "/api/v1/chatbots/messages/send",
        data=json.dumps({"bot_id": "b2", "message": "olá"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_allowed.status_code == 201


@pytest.mark.django_db
def test_workflows_execute_requires_permission(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="wtenant2", domain="wtenant2.localhost", name="WTenant2", plan="pro"
    )
    d = Domain.objects.get(domain="wtenant2.localhost")

    pw = gen_password()
    user = User.objects.create_user(username="wuser2", password=pw)
    p_exec = Permission.objects.create(code="workflows_execute")

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "wuser2", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    r_forbidden = client.post(
        "/api/v1/workflows/execute",
        data=json.dumps({"workflow_id": "wf1", "input": {"a": 1}}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_forbidden.status_code == 403

    UserPermission.objects.create(user=user, permission=p_exec, tenant=t)
    r_allowed = client.post(
        "/api/v1/workflows/execute",
        data=json.dumps({"workflow_id": "wf2", "input": {"b": 2}}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_allowed.status_code == 201


@pytest.mark.django_db
def test_ai_infer_requires_permission(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="atenant", domain="atenant.localhost", name="ATenant", plan="pro"
    )
    d = Domain.objects.get(domain="atenant.localhost")

    pw = gen_password()
    user = User.objects.create_user(username="auser", password=pw)
    p_infer = Permission.objects.create(code="ai_infer")

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "auser", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    r_forbidden = client.post(
        "/api/v1/ai/infer",
        data=json.dumps({"model": "m1", "prompt": "hi"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_forbidden.status_code == 403

    UserPermission.objects.create(user=user, permission=p_infer, tenant=t)
    r_allowed = client.post(
        "/api/v1/ai/infer",
        data=json.dumps({"model": "m2", "prompt": "hello"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert r_allowed.status_code == 201
