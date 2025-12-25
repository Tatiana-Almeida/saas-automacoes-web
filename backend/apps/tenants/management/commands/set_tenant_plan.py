from django.core.management.base import BaseCommand, CommandError
from apps.tenants.models import Tenant, Plan


class Command(BaseCommand):
    help = "Set the plan for an existing tenant."

    def add_arguments(self, parser):
        parser.add_argument("--schema", required=True, help="Schema name of the tenant")
        parser.add_argument(
            "--plan", required=True, help="Plan to set (free|pro|enterprise)"
        )

    def handle(self, *args, **options):
        schema = options["schema"]
        plan_input = options["plan"]
        try:
            tenant = Tenant.objects.get(schema_name=schema)
        except Tenant.DoesNotExist:
            raise CommandError(f"Tenant with schema {schema} not found")

        plan_obj = None
        try:
            plan_obj = Plan.objects.get(code=plan_input)
        except Plan.DoesNotExist:
            try:
                plan_obj = Plan.objects.get(name=plan_input)
            except Plan.DoesNotExist:
                plan_obj = None

        if plan_obj:
            tenant.plan_ref = plan_obj
            tenant.plan = plan_obj.code
            resolved = plan_obj.code
        else:
            tenant.plan_ref = None
            tenant.plan = plan_input
            resolved = plan_input

        tenant.save()
        self.stdout.write(
            self.style.SUCCESS(f"Tenant {schema} plan updated to {resolved}")
        )
