import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.rbac.models import Role, Permission, UserRole, UserPermission


class Command(BaseCommand):
    help = 'Apply bulk RBAC operations from a JSON file (assign/revoke roles and permissions)'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Path to JSON file with operations')

    def handle(self, *args, **options):
        path = options['file']
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tenant_schema = data.get('tenant')
        if not tenant_schema:
            return self.stdout.write(self.style.ERROR('Campo "tenant" obrigatório no JSON'))

        try:
            tenant = Tenant.objects.get(schema_name=tenant_schema)
        except Tenant.DoesNotExist:
            return self.stdout.write(self.style.ERROR('Tenant não encontrado'))

        User = get_user_model()

        def get_user(username):
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                raise ValueError(f'Usuário não encontrado: {username}')

        # Assign roles
        for item in (data.get('assign', {}).get('roles', []) or []):
            user = get_user(item['username'])
            role = Role.objects.get(name=item['role'])
            UserRole.objects.get_or_create(user=user, role=role, tenant=tenant)

        # Assign permissions
        for item in (data.get('assign', {}).get('permissions', []) or []):
            user = get_user(item['username'])
            perm = Permission.objects.get(code=item['permission'])
            UserPermission.objects.get_or_create(user=user, permission=perm, tenant=tenant)

        # Revoke roles
        for item in (data.get('revoke', {}).get('roles', []) or []):
            user = get_user(item['username'])
            role = Role.objects.get(name=item['role'])
            UserRole.objects.filter(user=user, role=role, tenant=tenant).delete()

        # Revoke permissions
        for item in (data.get('revoke', {}).get('permissions', []) or []):
            user = get_user(item['username'])
            perm = Permission.objects.get(code=item['permission'])
            UserPermission.objects.filter(user=user, permission=perm, tenant=tenant).delete()

        self.stdout.write(self.style.SUCCESS('Operações RBAC aplicadas com sucesso'))
