from rest_framework import serializers
from ..models import Notification, NotificationLog


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "user", "channel", "to", "title", "body", "payload", "status", "attempts", "last_error", "sent_at", "created_at", "updated_at")
        read_only_fields = ("id", "user", "status", "attempts", "last_error", "sent_at", "created_at", "updated_at")


class SendNotificationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    channel = serializers.ChoiceField(choices=['email','sms','whatsapp'])
    to = serializers.CharField(max_length=255)
    title = serializers.CharField(max_length=200)
    body = serializers.CharField(allow_blank=True, required=False)
    payload = serializers.JSONField(required=False)


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = ("id", "notification", "status", "attempt", "message", "response_payload", "metrics", "created_at")
        read_only_fields = fields
