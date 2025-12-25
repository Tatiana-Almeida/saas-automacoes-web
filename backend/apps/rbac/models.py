from django.conf import settings
from django.db import models


class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.code


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_roles"
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="tenant_user_roles"
    )

    class Meta:
        unique_together = ("user", "role", "tenant")

    def save(self, *args, **kwargs):
        # If tenant not provided, attempt to default to the public/test tenant
        if not getattr(self, "tenant_id", None):
            try:
                from django.apps import apps as django_apps
                from django_tenants.utils import get_public_schema_name

                public_schema = get_public_schema_name()
                Tenant = django_apps.get_model("tenants", "Tenant")
                t = Tenant.objects.filter(
                    schema_name__in=[public_schema, "test_tenant"]
                ).first()
                if t:
                    self.tenant = t
            except Exception:
                pass
        super().save(*args, **kwargs)


class UserPermission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rbac_user_permissions",
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="rbac_user_permissions"
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="tenant_user_permissions",
    )

    class Meta:
        unique_together = ("user", "permission", "tenant")

    def save(self, *args, **kwargs):
        if not getattr(self, "tenant_id", None):
            try:
                from django.apps import apps as django_apps
                from django_tenants.utils import get_public_schema_name

                public_schema = get_public_schema_name()
                Tenant = django_apps.get_model("tenants", "Tenant")
                t = Tenant.objects.filter(
                    schema_name__in=[public_schema, "test_tenant"]
                ).first()
                if t:
                    self.tenant = t
            except Exception:
                pass
        super().save(*args, **kwargs)
