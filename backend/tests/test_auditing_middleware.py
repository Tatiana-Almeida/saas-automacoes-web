import json
import pytest
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant, Domain
from apps.rbac.models import Permission, UserPermission
from apps.auditing.models import AuditLog

User = get_user_model()


@pytest.mark.django_db
def test_audit_middleware_records_login_logout_and_error(client, gen_password, create_tenant):
    t = create_tenant(schema_name='gamma', domain='gamma.localhost', name='Gamma', plan='pro')
    d = Domain.objects.get(domain='gamma.localhost')

    pw = gen_password()
    u = User.objects.create_user(username='auditor', password=pw)

    # Login -> action should be 'login'
    login = client.post(
        '/api/v1/auth/token',
        data=json.dumps({'username': 'auditor', 'password': pw}),
        content_type='application/json',
        HTTP_HOST=d.domain,
    )
    assert login.status_code == 200
    client.cookies['access_token'] = login.cookies['access_token'].value

    # Trigger an error (404)
    _404 = client.get('/api/v1/does-not-exist', HTTP_HOST=d.domain)
    assert _404.status_code == 404

    # Logout -> action should be 'logout'
    logout = client.post('/api/v1/auth/logout', data=json.dumps({}), content_type='application/json', HTTP_HOST=d.domain)
    assert logout.status_code in (200, 204)

    actions = list(AuditLog.objects.order_by('-created_at').values_list('action', flat=True)[:5])
    assert 'login' in actions
    assert 'error' in actions
    assert 'logout' in actions

    # Ensure tenant schema was captured for tenant-routed requests
    logs = AuditLog.objects.filter(tenant_schema='gamma')
    assert logs.exists()


@pytest.mark.django_db
def test_audit_logs_api_filters(client, gen_password, create_tenant):
    t = create_tenant(schema_name='delta', domain='delta.localhost', name='Delta', plan='pro')
    d = Domain.objects.get(domain='delta.localhost')

    pw = gen_password()
    admin = User.objects.create_user(username='admin_audit', password=pw)
    Permission.objects.create(code='view_audit_logs')
    # grant directly to admin for tenant t
    perm = Permission.objects.get(code='view_audit_logs')
    UserPermission.objects.create(user=admin, permission=perm, tenant=t)

    # Generate one login log
    login = client.post(
        '/api/v1/auth/token',
        data=json.dumps({'username': 'admin_audit', 'password': pw}),
        content_type='application/json',
        HTTP_HOST=d.domain,
    )
    assert login.status_code == 200
    client.cookies['access_token'] = login.cookies['access_token'].value

    # Query logs with filters (requires permission)
    resp = client.get('/api/v1/auditing/logs?action=login&tenant_schema=delta', HTTP_HOST=d.domain)
    assert resp.status_code == 200
    items = resp.json().get('results') if isinstance(resp.json(), dict) else resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1
