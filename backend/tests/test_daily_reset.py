import json
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from apps.tenants.models import Tenant, Domain
from apps.rbac.models import Permission, UserPermission

User = get_user_model()


@pytest.mark.django_db
def test_reset_daily_counters_for_category(client, gen_password, create_tenant):
    t = create_tenant(schema_name='acme', domain='acme.localhost', name='ACME', plan='free')
    d = Domain.objects.get(domain='acme.localhost')

    pw = gen_password()
    u = User.objects.create_user(username='admin_reset', password=pw, is_staff=True)
    p_manage = Permission.objects.get_or_create(code='manage_tenants')[0]
    UserPermission.objects.create(user=u, permission=p_manage, tenant=t)

    login = client.post(
        '/api/v1/auth/token',
        data=json.dumps({'username': 'admin_reset', 'password': pw}),
        content_type='application/json',
    )
    assert login.status_code == 200
    client.cookies['access_token'] = login.cookies['access_token'].value

    today = timezone.now().date().isoformat()
    key = f"plan_limit:{t.schema_name}:send_whatsapp:{today}"
    cache.set(key, 3, timeout=60)
    assert int(cache.get(key, 0)) == 3

    resp = client.post(
        '/api/v1/core/throttle/daily/reset',
        data=json.dumps({'categories': ['send_whatsapp']}),
        content_type='application/json',
        HTTP_HOST=d.domain,
    )
    assert resp.status_code == 200
    payload = resp.json()
    cats = payload.get('categories_reset', [])
    assert any(c.get('category') == 'send_whatsapp' and c.get('reset') for c in cats)

    # After reset, usage should be 0 (key deleted)
    assert int(cache.get(key, 0)) == 0


@pytest.mark.django_db
def test_reset_all_categories_when_none_provided(client, gen_password, create_tenant):
    t = create_tenant(schema_name='bravo', domain='bravo.localhost', name='Bravo', plan='free')
    d = Domain.objects.get(domain='bravo.localhost')

    pw = gen_password()
    u = User.objects.create_user(username='admin_reset_all', password=pw, is_staff=True)
    p_manage = Permission.objects.get_or_create(code='manage_tenants')[0]
    UserPermission.objects.create(user=u, permission=p_manage, tenant=t)

    login = client.post(
        '/api/v1/auth/token',
        data=json.dumps({'username': 'admin_reset_all', 'password': pw}),
        content_type='application/json',
    )
    assert login.status_code == 200
    client.cookies['access_token'] = login.cookies['access_token'].value

    today = timezone.now().date().isoformat()
    # Seed two categories with usage
    key1 = f"plan_limit:{t.schema_name}:send_email:{today}"
    key2 = f"plan_limit:{t.schema_name}:send_sms:{today}"
    cache.set(key1, 5, timeout=60)
    cache.set(key2, 7, timeout=60)
    assert int(cache.get(key1, 0)) == 5
    assert int(cache.get(key2, 0)) == 7

    # No categories provided: should reset all defined by plan; unknowns are safe to ignore
    resp = client.post(
        '/api/v1/core/throttle/daily/reset',
        data=json.dumps({}),
        content_type='application/json',
        HTTP_HOST=d.domain,
    )
    assert resp.status_code == 200

    assert int(cache.get(key1, 0)) == 0
    assert int(cache.get(key2, 0)) == 0
