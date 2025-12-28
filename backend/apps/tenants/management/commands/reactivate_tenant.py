from apps.tenants.models import Domain, Tenant
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Reativa um tenant por id, schema_name ou domain"

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, help="ID do tenant")
        parser.add_argument("--schema", type=str, help="schema_name do tenant")
        parser.add_argument("--domain", type=str, help="domain do tenant")

    def handle(self, *args, **options):
        tid = options.get("id")
        schema = options.get("schema")
        domain = options.get("domain")

        tenant = None
        if tid:
            tenant = Tenant.objects.filter(id=tid).first()
        elif schema:
            tenant = Tenant.objects.filter(schema_name=schema).first()
        elif domain:
            d = Domain.objects.filter(domain=domain).select_related("tenant").first()
            tenant = d.tenant if d else None

        if not tenant:
            raise CommandError("Tenant não encontrado")

        tenant.is_active = True
        tenant.save(update_fields=["is_active"])
        self.stdout.write(self.style.SUCCESS(f"Tenant {tenant.id} reativado"))
