from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from apps.auditing.models import AuditLog, AuditRetentionPolicy


class Command(BaseCommand):
    help = 'Remove audit logs older than a retention period (days). Supports per-tenant overrides.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=None, help='Retention in days (default from settings)')

    def handle(self, *args, **options):
        default_days = options['days'] if options['days'] is not None else getattr(settings, 'AUDIT_RETENTION_DEFAULT_DAYS', 90)
        overrides = getattr(settings, 'AUDIT_RETENTION_TENANT_DAYS', {}) or {}
        # Merge DB policies (admin-configured) into overrides
        try:
            db_policies = {p.tenant_schema or '': p.days for p in AuditRetentionPolicy.objects.all()}
            # If a global policy exists (tenant_schema empty), use it as default
            global_override = db_policies.get('')
            if global_override:
                default_days = int(global_override)
            # Per-tenant policies override settings
            for schema, days in db_policies.items():
                if schema:  # skip global key here
                    overrides[schema] = int(days)
        except Exception:
            pass
        now = timezone.now()

        total = 0
        # First purge per-tenant overrides
        for schema, days in overrides.items():
            try:
                days = int(days)
            except Exception:
                continue
            cutoff = now - timedelta(days=days)
            qs = AuditLog.objects.filter(tenant_schema=schema, created_at__lt=cutoff)
            cnt = qs.count()
            qs.delete()
            total += cnt

        # Then purge remaining with default
        remaining_qs = AuditLog.objects.exclude(tenant_schema__in=list(overrides.keys()))
        cutoff_default = now - timedelta(days=int(default_days))
        cnt_default = remaining_qs.filter(created_at__lt=cutoff_default).count()
        remaining_qs.filter(created_at__lt=cutoff_default).delete()
        total += cnt_default

        self.stdout.write(self.style.SUCCESS(
            f'Purged {total} audit logs (default {int(default_days)} days; overrides: { {k:int(v) for k,v in overrides.items()} })'
        ))
