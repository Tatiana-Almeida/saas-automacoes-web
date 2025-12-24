from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Plan(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    daily_limits = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code}"

class Tenant(TenantMixin):
    name = models.CharField(max_length=200)
    plan = models.CharField(max_length=50, default='free')
    plan_ref = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.SET_NULL, related_name='tenants')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    auto_create_schema = True

class Domain(DomainMixin):
    def save(self, *args, **kwargs):
        """Always persist Domain records in the public schema.

        Tests (and some runtime flows) may call Domain.objects.create() while
        the DB connection is currently set to a tenant schema. Ensure Domain
        rows are stored in the public schema.
        """
        try:
            from django.db import connection
            prev = getattr(connection, 'schema_name', None)
            try:
                connection.set_schema_to_public()
            except Exception:
                pass
            return super().save(*args, **kwargs)
        finally:
            try:
                if prev:
                    connection.set_schema(prev)
            except Exception:
                pass
