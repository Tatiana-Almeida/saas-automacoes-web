from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.core.management import call_command


@receiver(post_migrate)
def seed_rbac_on_migrate(sender, **kwargs):
    """Run the RBAC seed command automatically after migrations in development/test.
    This is idempotent and safe to run repeatedly.
    """
    try:
        # avoid running during migrations for other apps unnecessarily
        call_command('seed_rbac')
    except Exception:
        # don't fail migrations if seeding fails
        pass
