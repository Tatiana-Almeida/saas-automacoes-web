import pytest
from django.contrib.auth import get_user_model

@pytest.mark.django_db
def test_core_queues_status_admin_only(client, gen_password, create_tenant):
    User = get_user_model()
    # Create tenant/domain to provide host context
    from apps.tenants.models import Domain
    t = create_tenant(schema_name='acme', domain='acme.localhost', name='Acme', plan='free')
    d = Domain.objects.get(domain='acme.localhost')

    # Create staff user (admin)
    pw = gen_password()
    u = User.objects.create_user(username='admin', password=pw, is_staff=True)

    # Login to obtain access token
    login = client.post('/api/v1/auth/token', data={'username': 'admin', 'password': pw}, content_type='application/json')
    assert login.status_code == 200
    client.cookies['access_token'] = login.cookies['access_token'].value

    # Call queues status
    resp = client.get('/api/v1/core/queues/status', HTTP_HOST=d.domain)
    assert resp.status_code == 200
    data = resp.json()
    assert 'celery' in data
    assert 'dlq' in data

@pytest.mark.django_db
def test_core_queues_status_forbidden_for_non_admin(client, gen_password, create_tenant):
    User = get_user_model()
    from apps.tenants.models import Domain
    t = create_tenant(schema_name='acme', domain='acme.localhost', name='Acme', plan='free')
    d = Domain.objects.get(domain='acme.localhost')

    pw = gen_password()
    u = User.objects.create_user(username='user', password=pw, is_staff=False)

    login = client.post('/api/v1/auth/token', data={'username': 'user', 'password': pw}, content_type='application/json')
    assert login.status_code == 200
    client.cookies['access_token'] = login.cookies['access_token'].value

    resp = client.get('/api/v1/core/queues/status', HTTP_HOST=d.domain)
    assert resp.status_code == 403
