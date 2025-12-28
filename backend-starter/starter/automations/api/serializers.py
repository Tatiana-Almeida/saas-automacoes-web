from rest_framework import serializers

from ..models import Automation, AutomationLog


class AutomationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Automation
        fields = (
            "id",
            "user",
            "name",
            "type",
            "is_active",
            "configuration",
            "last_run_at",
            "last_status",
            "last_error",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "last_run_at",
            "last_status",
            "last_error",
            "created_at",
            "updated_at",
        )


class AutomationLogSerializer(serializers.ModelSerializer):
    duration_ms = serializers.SerializerMethodField()

    class Meta:
        model = AutomationLog
        fields = (
            "id",
            "automation",
            "status",
            "error_message",
            "output_payload",
            "started_at",
            "finished_at",
            "duration_ms",
            "created_at",
        )
        read_only_fields = (
            "id",
            "automation",
            "status",
            "error_message",
            "output_payload",
            "started_at",
            "finished_at",
            "duration_ms",
            "created_at",
        )

    def get_duration_ms(self, obj):
        return obj.duration_ms
