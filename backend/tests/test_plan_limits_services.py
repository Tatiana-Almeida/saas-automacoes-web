import json
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.tenants.models import Tenant, Domain
from apps.rbac.models import Permission, UserPermission

User = get_user_model()


@pytest.mark.django_db
@override_settings(
    TENANT_PLAN_DAILY_LIMITS={
        "free": {
            "email_send": 1,
        }
    }
)
def test_daily_limit_enforcement_email(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="mailco", domain="mailco.localhost", name="MailCo", plan="free"
    )
    d = Domain.objects.get(domain="mailco.localhost")

    pw = gen_password()
    u = User.objects.create_user(username="mailer", password=pw, is_staff=True)
    p = Permission.objects.create(code="email_send")
    UserPermission.objects.create(user=u, permission=p, tenant=t)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "mailer", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    # First send allowed
    resp1 = client.post(
        "/api/v1/email/messages/send",
        data=json.dumps({"to": "user@example.com", "subject": "Hi", "body": "Hello"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert 200 <= resp1.status_code < 300

    # Second send blocked by daily limit
    resp2 = client.post(
        "/api/v1/email/messages/send",
        data=json.dumps(
            {"to": "user@example.com", "subject": "Hi2", "body": "Hello again"}
        ),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp2.status_code == 429
    data = resp2.json()
    assert data.get("category") == "email_send"
    assert data.get("plan") == "free"


@pytest.mark.django_db
@override_settings(
    TENANT_PLAN_DAILY_LIMITS={
        "free": {
            "sms_send": 1,
        }
    }
)
def test_daily_limit_enforcement_sms(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="smsco", domain="smsco.localhost", name="SmsCo", plan="free"
    )
    d = Domain.objects.get(domain="smsco.localhost")

    pw = gen_password()
    u = User.objects.create_user(username="smsuser", password=pw, is_staff=True)
    p = Permission.objects.create(code="sms_send")
    UserPermission.objects.create(user=u, permission=p, tenant=t)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "smsuser", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    resp1 = client.post(
        "/api/v1/sms/messages/send",
        data=json.dumps({"to": "+15550001234", "message": "Ping"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert 200 <= resp1.status_code < 300

    resp2 = client.post(
        "/api/v1/sms/messages/send",
        data=json.dumps({"to": "+15550001234", "message": "Ping2"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp2.status_code == 429
    data = resp2.json()
    assert data.get("category") == "sms_send"
    assert data.get("plan") == "free"


@pytest.mark.django_db
@override_settings(
    TENANT_PLAN_DAILY_LIMITS={
        "free": {
            "chatbots_send": 1,
        }
    }
)
def test_daily_limit_enforcement_chatbots(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="botco", domain="botco.localhost", name="BotCo", plan="free"
    )
    d = Domain.objects.get(domain="botco.localhost")

    pw = gen_password()
    u = User.objects.create_user(username="botuser", password=pw, is_staff=True)
    p = Permission.objects.create(code="chatbots_send")
    UserPermission.objects.create(user=u, permission=p, tenant=t)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "botuser", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    resp1 = client.post(
        "/api/v1/chatbots/messages/send",
        data=json.dumps({"bot_id": "bot-1", "message": "Hello", "session_id": "s1"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert 200 <= resp1.status_code < 300

    resp2 = client.post(
        "/api/v1/chatbots/messages/send",
        data=json.dumps(
            {"bot_id": "bot-1", "message": "Hello again", "session_id": "s1"}
        ),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp2.status_code == 429
    data = resp2.json()
    assert data.get("category") == "chatbots_send"
    assert data.get("plan") == "free"


@pytest.mark.django_db
@override_settings(
    TENANT_PLAN_DAILY_LIMITS={
        "free": {
            "workflows_execute": 1,
        }
    }
)
def test_daily_limit_enforcement_workflows(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="flowco", domain="flowco.localhost", name="FlowCo", plan="free"
    )
    d = Domain.objects.get(domain="flowco.localhost")

    pw = gen_password()
    u = User.objects.create_user(username="wfuser", password=pw, is_staff=True)
    p = Permission.objects.create(code="workflows_execute")
    UserPermission.objects.create(user=u, permission=p, tenant=t)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "wfuser", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    resp1 = client.post(
        "/api/v1/workflows/execute",
        data=json.dumps({"workflow_id": "wf-1", "input": {"x": 1}}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert 200 <= resp1.status_code < 300

    resp2 = client.post(
        "/api/v1/workflows/execute",
        data=json.dumps({"workflow_id": "wf-1", "input": {"x": 2}}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp2.status_code == 429
    data = resp2.json()
    assert data.get("category") == "workflows_execute"
    assert data.get("plan") == "free"


@pytest.mark.django_db
@override_settings(
    TENANT_PLAN_DAILY_LIMITS={
        "free": {
            "ai_infer": 1,
        }
    }
)
def test_daily_limit_enforcement_ai(client, gen_password, create_tenant):
    t = create_tenant(
        schema_name="aico", domain="aico.localhost", name="AiCo", plan="free"
    )
    d = Domain.objects.get(domain="aico.localhost")

    pw = gen_password()
    u = User.objects.create_user(username="aiuser", password=pw, is_staff=True)
    p = Permission.objects.create(code="ai_infer")
    UserPermission.objects.create(user=u, permission=p, tenant=t)

    login = client.post(
        "/api/v1/auth/token",
        data=json.dumps({"username": "aiuser", "password": pw}),
        content_type="application/json",
    )
    assert login.status_code == 200
    client.cookies["access_token"] = login.cookies["access_token"].value

    resp1 = client.post(
        "/api/v1/ai/infer",
        data=json.dumps({"model": "tiny", "prompt": "Hello"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert 200 <= resp1.status_code < 300

    resp2 = client.post(
        "/api/v1/ai/infer",
        data=json.dumps({"model": "tiny", "prompt": "Hello again"}),
        content_type="application/json",
        HTTP_HOST=d.domain,
    )
    assert resp2.status_code == 429
    data = resp2.json()
    assert data.get("category") == "ai_infer"
    assert data.get("plan") == "free"
