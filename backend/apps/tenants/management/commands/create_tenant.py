from apps.tenants.models import Domain, Tenant
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create a tenant schema and its primary domain."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Tenant name")
        parser.add_argument(
            "--schema", required=True, help="Schema name (e.g., client1)"
        )
        parser.add_argument(
            "--domain", required=True, help="Primary domain (e.g., client1.localhost)"
        )
        parser.add_argument(
            "--plan", default="free", help="Plan name (free|pro|enterprise)"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        name = options["name"]
        schema = options["schema"]
        domain_name = options["domain"]
        plan = options["plan"]

        if Tenant.objects.filter(schema_name=schema).exists():
            raise CommandError(f"Tenant schema {schema} already exists")

        tenant = Tenant(schema_name=schema, name=name, plan=plan)
        tenant.save()  # auto_create_schema = True will create the schema

        Domain.objects.create(domain=domain_name, tenant=tenant, is_primary=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"Tenant created: {name} ({schema}) with domain {domain_name} and plan {plan}"
            )
        )
