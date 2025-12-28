from rest_framework import serializers

from ..models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ("id", "user", "plan", "status", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
