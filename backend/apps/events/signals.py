from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .events import USER_CREATED, emit_event

User = get_user_model()


@receiver(post_save, sender=User)
def emit_user_created(sender, instance, created, **kwargs):
    if created:
        try:
            tenant = getattr(instance, "tenant", None)
            emit_event(
                USER_CREATED,
                {
                    "user_id": instance.id,
                    "username": getattr(instance, "username", None),
                    "tenant_id": getattr(tenant, "id", None),
                    "tenant_schema": getattr(tenant, "schema_name", None),
                },
            )
        except Exception:
            pass
