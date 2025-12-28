from apps.auditing.models import AuditLog
from apps.tenants.models import Tenant
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


def daily_limits_for(tenant):
    plan_obj = getattr(tenant, "plan_ref", None)
    try:
        dl = getattr(plan_obj, "daily_limits", None)
        if isinstance(dl, dict):
            return dl
    except Exception:
        pass
    plan_code = getattr(plan_obj, "code", None) or getattr(tenant, "plan", "free")
    return settings.TENANT_PLAN_DAILY_LIMITS.get(plan_code, {})


class Command(BaseCommand):
    help = "Reset today's per-tenant daily counters for categories. Use --schema to target a tenant or --all to reset all tenants."

    def add_arguments(self, parser):
        parser.add_argument("--schema", type=str, help="Tenant schema_name to reset")
        parser.add_argument("--all", action="store_true", help="Reset for all tenants")
        parser.add_argument(
            "--categories",
            nargs="*",
            help="Categories to reset (default: all categories from tenant plan)",
        )

    def handle(self, *args, **options):
        schema = options.get("schema")
        reset_all = options.get("all")
        categories = options.get("categories") or []

        if not schema and not reset_all:
            raise CommandError("Provide --schema <name> or --all")

        if reset_all:
            tenants = Tenant.objects.all()
        else:
            try:
                tenants = [Tenant.objects.get(schema_name=schema)]
            except Tenant.DoesNotExist:
                raise CommandError(f"Tenant with schema_name={schema} not found")

        today = timezone.now().date().isoformat()
        total_keys = 0
        for tenant in tenants:
            schema_name = getattr(tenant, "schema_name", None)
            if not schema_name:
                continue
            cfg = daily_limits_for(tenant)
            cats = categories or list(cfg.keys())
            for cat in cats:
                key = f"plan_limit:{schema_name}:{cat}:{today}"
                try:
                    cache.delete(key)
                    total_keys += 1
                except Exception:
                    pass

        self.stdout.write(
            self.style.SUCCESS(
                f"Reset complete: tenants={len(tenants)}, keys_cleared={total_keys}"
            )
        )
        # Create a single audit entry summarizing the CLI action
        try:
            AuditLog.objects.create(
                user=None,
                path=f"/cli/reset_daily_counters?tenants={len(tenants)}&keys={total_keys}",
                method="CLI",
                ip_address=None,
            )
        except Exception:
            pass
