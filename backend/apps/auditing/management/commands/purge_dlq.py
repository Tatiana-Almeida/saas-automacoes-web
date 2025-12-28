from apps.auditing.models import AuditLog
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Purge DLQ (AuditLog entries with action='event_DLQ') older than N days."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            help="Purge DLQ entries older than this number of days (default from settings)",
        )

    def handle(self, *args, **options):
        days = options.get("days")
        if days is None:
            days = getattr(settings, "AUDIT_DLQ_PURGE_DAYS", 30)
        cutoff = timezone.now() - timezone.timedelta(days=int(days))
        qs = AuditLog.objects.filter(action="event_DLQ", created_at__lt=cutoff)
        count = qs.count()
        qs.delete()
        self.stdout.write(
            self.style.SUCCESS(f"Purged {count} DLQ log(s) older than {days} days")
        )
