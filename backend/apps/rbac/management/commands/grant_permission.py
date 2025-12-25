from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant
from apps.rbac.models import Permission, UserPermission


class Command(BaseCommand):
    help = "Grant a permission to a user within a tenant schema"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Target username")
        parser.add_argument(
            "--permission", required=True, help="Permission code (e.g., send_whatsapp)"
        )
        parser.add_argument(
            "--tenant", required=True, help="Tenant schema_name (e.g., acme)"
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        perm_code = options["permission"]
        tenant_schema = options["tenant"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return self.stdout.write(self.style.ERROR("Usuário não encontrado"))

        try:
            perm = Permission.objects.get(code=perm_code)
        except Permission.DoesNotExist:
            return self.stdout.write(self.style.ERROR("Permissão não encontrada"))

        try:
            tenant = Tenant.objects.get(schema_name=tenant_schema)
        except Tenant.DoesNotExist:
            return self.stdout.write(self.style.ERROR("Tenant não encontrado"))

        UserPermission.objects.get_or_create(user=user, permission=perm, tenant=tenant)
        return self.stdout.write(
            self.style.SUCCESS(
                f'Permissão "{perm_code}" concedida ao usuário "{username}" no tenant "{tenant_schema}"'
            )
        )
