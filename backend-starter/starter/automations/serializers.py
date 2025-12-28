from rest_framework import serializers

from .models import Automation


class AutomationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Automation
        fields = ("id", "name", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
