from django.core.management.base import BaseCommand

from django.core.management.base import BaseCommand
from contextlib import contextmanager
from django.db import transaction

from ...models import Role, Permission


def _noop_context(*args, **kwargs):
    @contextmanager
    def _ctx():
        yield

    return _ctx()


class Command(BaseCommand):
    help = 'Seed default RBAC roles and permissions (supports --tenant and --all-tenants)'

    def add_arguments(self, parser):
        parser.add_argument('--tenant', help='Schema name of tenant to seed (defaults to public)', required=False)
        parser.add_argument('--all-tenants', action='store_true', help='Seed all tenants (requires django-tenants)', required=False)

    def handle(self, *args, **options):
        # Prepare context manager for tenant schema switching if available
        try:
            from django_tenants.utils import schema_context, get_public_schema_name
        except Exception:
            schema_context = _noop_context
            try:
                # best-effort fallback
                from django_tenants.utils import get_public_schema_name
            except Exception:
                get_public_schema_name = lambda: 'public'

        tenant_arg = options.get('tenant')
        all_tenants = options.get('all_tenants')

        def seed_in_schema(schema_name=None):
            ctx = schema_context(schema_name) if schema_name else schema_context(get_public_schema_name())
            with ctx:
                perms = [
                    {'code': 'manage_users', 'description': 'Gerenciar usuários'},
                    {'code': 'view_users', 'description': 'Ver usuários'},
                    {'code': 'manage_rbac', 'description': 'Gerenciar roles e permissões'},
                    {'code': 'manage_tenants', 'description': 'Gerenciar tenants'},
                ]
                created_perms = []
                for p in perms:
                    perm, created = Permission.objects.get_or_create(code=p['code'], defaults={'description': p.get('description', '')})
                    created_perms.append(perm)
                    if created:
                        self.stdout.write(self.style.SUCCESS(f"[{schema_name or 'default'}] Created permission: {perm.code}"))

                # Roles
                admin_role, created = Role.objects.get_or_create(name='ADMIN')
                if created:
                    self.stdout.write(self.style.SUCCESS(f'[{schema_name or "default"}] Created role: ADMIN'))
                cliente_role, created = Role.objects.get_or_create(name='CLIENTE')
                if created:
                    self.stdout.write(self.style.SUCCESS(f'[{schema_name or "default"}] Created role: CLIENTE'))

                # Assign permissions to ADMIN (all)
                with transaction.atomic():
                    admin_role.permissions.set(Permission.objects.all())
                    admin_role.save()

                    # Assign a minimal set to CLIENTE
                    cliente_perms = Permission.objects.filter(code__in=['view_users'])
                    cliente_role.permissions.set(cliente_perms)
                    cliente_role.save()

        # If requested, seed all tenants (requires tenants app + django-tenants)
        if all_tenants:
            try:
                from django.apps import apps as django_apps
                Tenant = django_apps.get_model('tenants', 'Tenant')
                try:
                    from django_tenants.utils import schema_context as _schema_context
                    schema_ctx = _schema_context
                except Exception:
                    schema_ctx = schema_context
                for t in Tenant.objects.all():
                    try:
                        seed_in_schema(t.schema_name)
                    except Exception:
                        # don't fail the whole run
                        self.stderr.write(f'Failed to seed tenant {t.schema_name}')
            except Exception:
                self.stderr.write('Unable to enumerate tenants; ensure apps.tenants is installed and migrations applied')
                # fall back to single-schema seed
                seed_in_schema(None)
            self.stdout.write(self.style.SUCCESS('RBAC seed completed (all tenants)'))
            return

        # If a single tenant was supplied, seed only that schema
        if tenant_arg:
            try:
                seed_in_schema(tenant_arg)
                self.stdout.write(self.style.SUCCESS(f'RBAC seed completed for tenant {tenant_arg}'))
                return
            except Exception:
                self.stderr.write(f'Failed to seed tenant {tenant_arg}; falling back to default schema')

        # Default: seed public/default schema
        seed_in_schema(None)
        self.stdout.write(self.style.SUCCESS('RBAC seed completed'))
