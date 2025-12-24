import json
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.tenants.models import Tenant, Domain
from apps.rbac.models import Permission, UserPermission

User = get_user_model()


@pytest.mark.django_db
@override_settings(TENANT_PLAN_DAILY_LIMITS={
    'free': {
        'send_whatsapp': 2,
        'email_send': 2,
        'sms_send': 2,
        'chatbots_send': 2,
        'workflows_execute': 2,
        'ai_infer': 2,
    }
})
def test_daily_summary_counts_after_single_requests(client, create_tenant):
    t = create_tenant(schema_name='omega', domain='omega.localhost', name='Omega', plan='free')
    d = Domain.objects.get(domain='omega.localhost')

    u = User.objects.create_user(username='smoker', password='Test123!', is_staff=True)

    # Ensure permissions exist and are granted to the user for this tenant
    perms = [
        'send_whatsapp', 'email_send', 'sms_send',
        'chatbots_send', 'workflows_execute', 'ai_infer'
    ]
    for code in perms:
        p, _ = Permission.objects.get_or_create(code=code)
        UserPermission.objects.get_or_create(user=u, permission=p, tenant=t)

    # Login
    login = client.post(
        '/api/v1/auth/token',
        data=json.dumps({'username': 'smoker', 'password': 'Test123!'}),
        content_type='application/json',
    )
    assert login.status_code == 200
    client.cookies['access_token'] = login.cookies['access_token'].value

    # One request per category (all should be accepted)
    # WhatsApp
    r1 = client.post('/api/v1/whatsapp/messages/send',
                     data=json.dumps({'to': '+15550000000', 'message': 'hi'}),
                     content_type='application/json', HTTP_HOST=d.domain)
    assert 200 <= r1.status_code < 300

    # Email
    r2 = client.post('/api/v1/email/messages/send',
                     data=json.dumps({'to': 'user@example.com', 'subject': 's', 'body': 'b'}),
                     content_type='application/json', HTTP_HOST=d.domain)
    assert 200 <= r2.status_code < 300

    # SMS
    r3 = client.post('/api/v1/sms/messages/send',
                     data=json.dumps({'to': '+15550000001', 'message': 'h'}),
                     content_type='application/json', HTTP_HOST=d.domain)
    assert 200 <= r3.status_code < 300

    # Chatbots
    r4 = client.post('/api/v1/chatbots/messages/send',
                     data=json.dumps({'bot_id': 'b1', 'message': 'm', 'session_id': 's1'}),
                     content_type='application/json', HTTP_HOST=d.domain)
    assert 200 <= r4.status_code < 300

    # Workflows
    r5 = client.post('/api/v1/workflows/execute',
                     data=json.dumps({'workflow_id': 'wf1', 'input': {'x': 1}}),
                     content_type='application/json', HTTP_HOST=d.domain)
    assert 200 <= r5.status_code < 300

    # AI
    r6 = client.post('/api/v1/ai/infer',
                     data=json.dumps({'model': 'tiny', 'prompt': 'p'}),
                     content_type='application/json', HTTP_HOST=d.domain)
    assert 200 <= r6.status_code < 300

    # Fetch daily summary and assert used_today == 1 for all categories
    summary = client.get('/api/v1/core/throttle/daily/summary', HTTP_HOST=d.domain)
    assert summary.status_code == 200
    payload = summary.json()
    daily = {item['category']: item for item in payload.get('daily', [])}

    for cat in ['send_whatsapp', 'email_send', 'sms_send', 'chatbots_send', 'workflows_execute', 'ai_infer']:
        assert daily.get(cat), f"Category {cat} missing from daily summary"
        assert daily[cat]['used_today'] == 1
        # Remaining should be 1 given we set limit to 2
        assert daily[cat]['remaining_today'] == 1
