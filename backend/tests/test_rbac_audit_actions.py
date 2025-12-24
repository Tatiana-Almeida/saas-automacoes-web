import json
import pytest
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant, Domain
from apps.rbac.models import Role, Permission, UserPermission
from apps.auditing.models import AuditLog
from apps.auditing import tasks as audit_tasks

User = get_user_model()


@pytest.mark.django_db
def test_rbac_assign_logs_action_and_triggers_alert(monkeypatch, client, create_tenant):
    t = create_tenant(schema_name='omega', domain='omega.localhost', name='Omega', plan='pro')
    d = Domain.objects.get(domain='omega.localhost')

    admin = User.objects.create_user(username='admin_rbac', password='Test123!')
    target = User.objects.create_user(username='target_rbac', password='Test123!')

    role = Role.objects.create(name='Viewer')
    p_manage = Permission.objects.create(code='manage_users')
    UserPermission.objects.create(user=admin, permission=p_manage, tenant=t)

    login = client.post(
        '/api/v1/auth/token',
        data=json.dumps({'username': 'admin_rbac', 'password': 'Test123!'}),
        content_type='application/json',
    )
    assert login.status_code == 200
    client.cookies['access_token'] = login.cookies['access_token'].value

    calls = {'n': 0}
    monkeypatch.setattr(audit_tasks.send_audit_alert, 'delay', staticmethod(lambda *_args, **_kw: calls.__setitem__('n', calls['n'] + 1)))
    # Enable alerts and mark rbac_change as critical
    from django.test import override_settings
    with override_settings(ALERT_WEBHOOK_ENABLED=True, AUDIT_CRITICAL_ACTIONS=['rbac_change']):
        resp = client.post(
            f'/api/v1/rbac/users/{target.id}/roles/assign',
            data=json.dumps({'role': 'Viewer'}),
            content_type='application/json',
            HTTP_HOST=d.domain,
        )
        assert resp.status_code == 200

        # AuditLog with action rbac_change should exist
        assert AuditLog.objects.filter(action='rbac_change', tenant_schema='omega').exists()
        # And alert enqueued once
        assert calls['n'] == 1
