from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    path = models.CharField(max_length=1024)
    method = models.CharField(max_length=10)
    source = models.CharField(max_length=20, default="middleware")
    action = models.CharField(max_length=50, default="request")
    status_code = models.IntegerField(null=True, blank=True)
    tenant_schema = models.CharField(max_length=63, null=True, blank=True)
    tenant_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    payload = models.JSONField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["user"]),
            models.Index(fields=["source"]),
            models.Index(fields=["tenant_schema"]),
            models.Index(fields=["action"]),
        ]


class AuditRetentionPolicy(models.Model):
    """Configura retenção de auditoria por tenant (ou global).

    Se `tenant_schema` estiver vazio/nulo, considere como política global
    (usar apenas uma entrada global por convenção).
    """

    tenant_schema = models.CharField(max_length=63, null=True, blank=True)
    days = models.PositiveIntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["tenant_schema"]),
        ]
        verbose_name = "Audit Retention Policy"
        verbose_name_plural = "Audit Retention Policies"

    def __str__(self):
        tgt = self.tenant_schema or "GLOBAL"
        return f"{tgt}: {self.days} days"
