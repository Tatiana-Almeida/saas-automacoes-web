from django.core.management import call_command
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Tenant


@receiver(post_save, sender=Tenant)
def seed_rbac_on_tenant_create(sender, instance: Tenant, created, **kwargs):
    """When a tenant is created, seed RBAC defaults into its schema.

    This is best-effort and will not raise on failure.
    """
    if not created:
        return
    try:
        # call management command to seed this tenant schema
        call_command("seed_rbac", "--tenant", instance.schema_name)
    except Exception:
        # never fail tenant creation due to seeding errors
        return
