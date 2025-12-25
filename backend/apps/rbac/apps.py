from django.apps import AppConfig


class RbacConfig(AppConfig):
    name = "apps.rbac"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Import signal handlers to auto-seed RBAC after migrations
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
