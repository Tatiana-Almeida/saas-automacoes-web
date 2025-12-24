from rest_framework import serializers
from .models import AuditLog, AuditRetentionPolicy


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'username', 'path', 'method', 'source', 'action', 'status_code',
            'tenant_schema', 'tenant_id', 'ip_address', 'created_at'
        ]

    def get_username(self, obj):
        return getattr(obj.user, 'username', None) if obj.user else None


class AuditRetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditRetentionPolicy
        fields = ['id', 'tenant_schema', 'days']
