from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.management import call_command


User = get_user_model()


class RbacAdminAPITest(TestCase):
    def setUp(self):
        # create admin user and authenticate
        self.client = Client()
        self.admin = User.objects.create_superuser(email='admin@example.com', password='pass1234')
        # ensure RBAC seed ran
        try:
            call_command('seed_rbac')
        except Exception:
            pass
        # Ensure ADMIN/CLIENTE roles exist for tests
        from apps.rbac.models import Role
        Role.objects.get_or_create(name='ADMIN')
        Role.objects.get_or_create(name='CLIENTE')
        # Ensure default permissions exist
        from apps.rbac.models import Permission
        for code in ('manage_users', 'view_users', 'manage_rbac', 'manage_tenants'):
            Permission.objects.get_or_create(code=code, defaults={'description': code})
        self.client.force_login(self.admin)

    def test_create_permission_and_role(self):
        # create a permission
        perm_resp = self.client.post(reverse('rbac-permissions'), data={'code': 'test_perm', 'description': 'desc'})
        self.assertEqual(perm_resp.status_code, 201)
        from apps.rbac.models import Permission, Role
        p = Permission.objects.get(code='test_perm')

        # create a role with the permission
        role_resp = self.client.post(reverse('rbac-roles'), data={'name': 'TestRole', 'permissions': ['test_perm']}, content_type='application/json')
        self.assertEqual(role_resp.status_code, 201)
        r = Role.objects.get(name='TestRole')
        self.assertTrue(p in r.permissions.all())

    def test_list_roles_permissions(self):
        # ensure the seed ran and ADMIN exists
        from apps.rbac.models import Role, Permission
        Role.objects.get(name='ADMIN')
        Permission.objects.get(code='manage_users')
        roles_resp = self.client.get(reverse('rbac-roles'))
        self.assertEqual(roles_resp.status_code, 200)
        perms_resp = self.client.get(reverse('rbac-permissions'))
        self.assertEqual(perms_resp.status_code, 200)
