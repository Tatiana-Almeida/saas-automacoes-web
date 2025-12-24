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
    }
})
def test_daily_limit_enforcement_whatsapp(client, gen_password, create_tenant):
    # Setup tenant and domain (free plan)
    t = create_tenant(schema_name='acme', domain='acme.localhost', name='ACME', plan='free')
    d = Domain.objects.get(domain='acme.localhost')

    # Create user and grant permission
    pw = gen_password()
    u = User.objects.create_user(username='lim_user', password=pw, is_staff=True)
    p_send = Permission.objects.create(code='send_whatsapp')
    UserPermission.objects.create(user=u, permission=p_send, tenant=t)

    # Login
    login = client.post(
        '/api/v1/auth/token',
        data=json.dumps({'username': 'lim_user', 'password': pw}),
        content_type='application/json',
    )
    assert login.status_code == 200
    client.cookies['access_token'] = login.cookies['access_token'].value

    # First two sends allowed
    for i in range(2):
        resp = client.post(
            '/api/v1/whatsapp/messages/send',
            data=json.dumps({'to': '+5511999999999', 'message': f'Olá {i}'}),
            content_type='application/json',
            HTTP_HOST=d.domain,
        )
        assert 200 <= resp.status_code < 300

    # Third send should be blocked by daily limit
    resp3 = client.post(
        '/api/v1/whatsapp/messages/send',
        data=json.dumps({'to': '+5511999999999', 'message': 'Excesso'}),
        content_type='application/json',
        HTTP_HOST=d.domain,
    )
    assert resp3.status_code == 429
    data = resp3.json()
    assert data.get('category') == 'send_whatsapp'
    assert data.get('plan') == 'free'


@pytest.mark.django_db
def test_throttle_status_includes_daily_usage(client, gen_password, create_tenant):
    # Tenant and domain
    t = create_tenant(schema_name='bravo', domain='bravo.localhost', name='Bravo', plan='free')
    d = Domain.objects.get(domain='bravo.localhost')

    # Staff/admin user
    pw = gen_password()
    u = User.objects.create_user(username='admin_view', password=pw, is_staff=True)

    # Login
    login = client.post(
        '/api/v1/auth/token',
        data=json.dumps({'username': 'admin_view', 'password': pw}),
        content_type='application/json',
    )
    assert login.status_code == 200
    client.cookies['access_token'] = login.cookies['access_token'].value

    # Call status endpoint within tenant
    status_resp = client.get('/api/v1/core/throttle/status', HTTP_HOST=d.domain)
    assert status_resp.status_code == 200
    payload = status_resp.json()
    assert payload.get('schema') == 'bravo'
    assert 'daily' in payload
    # Daily should be a list of categories with limits
    assert isinstance(payload['daily'], list)
