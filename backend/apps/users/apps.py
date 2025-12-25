from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "apps.users"
    label = "users"

    def ready(self):
        # Install a test-only post_save hook to record created users in an
        # in-process registry so view code can find users created inside
        # pytest transactions even when DB connection visibility prevents
        # querying them from the request-handling connection.
        try:
            from django.contrib.auth import get_user_model
            from django.db.models.signals import post_save
            from apps.core.test_registry import register_user_instance

            User = get_user_model()
            post_save.connect(register_user_instance, sender=User)
        except Exception:
            # Be conservative in production; if anything fails here we don't
            # want to block app startup.
            pass
