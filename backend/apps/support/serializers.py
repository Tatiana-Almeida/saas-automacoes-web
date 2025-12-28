from rest_framework import serializers

from .models import SupportTicket


class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "user",
            "email",
            "subject",
            "message",
            "status",
            "response",
            "responder",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "response",
            "responder",
            "created_at",
            "updated_at",
        ]


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ["id", "email", "subject", "message"]


class SupportTicketResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ["id", "status", "response"]
