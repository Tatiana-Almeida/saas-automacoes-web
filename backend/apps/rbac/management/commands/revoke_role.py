from apps.rbac.models import Role, UserRole
from apps.tenants.models import Tenant
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Revoke a role from a user within a tenant schema"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Target username")
        parser.add_argument("--role", required=True, help="Role name (e.g., Viewer)")
        parser.add_argument(
            "--tenant", required=True, help="Tenant schema_name (e.g., acme)"
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        role_name = options["role"]
        tenant_schema = options["tenant"]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return self.stdout.write(self.style.ERROR("Usuário não encontrado"))

        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            return self.stdout.write(self.style.ERROR("Role não encontrada"))

        try:
            tenant = Tenant.objects.get(schema_name=tenant_schema)
        except Tenant.DoesNotExist:
            return self.stdout.write(self.style.ERROR("Tenant não encontrado"))

        deleted, _ = UserRole.objects.filter(
            user=user, role=role, tenant=tenant
        ).delete()
        if deleted:
            return self.stdout.write(
                self.style.SUCCESS(
                    f'Role "{role_name}" revogada do usuário "{username}" no tenant "{tenant_schema}"'
                )
            )
        return self.stdout.write("Nada para revogar")
