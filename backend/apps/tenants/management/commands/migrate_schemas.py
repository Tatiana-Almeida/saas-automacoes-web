from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "No-op migrate_schemas for test environments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--shared", action="store_true", help="Run shared migrations (ignored)"
        )
        parser.add_argument(
            "--noinput",
            action="store_true",
            dest="noinput",
            help="Do not prompt for input",
        )

    def handle(self, *args, **options):
        # In test environments we don't need tenant-specific schema migrations.
        # Provide a no-op command so tests invoking `migrate_schemas` don't fail.
        self.stdout.write(self.style.SUCCESS("migrate_schemas: no-op for tests"))
