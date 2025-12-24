from rest_framework import serializers


class ChatbotMessageSerializer(serializers.Serializer):
    bot_id = serializers.CharField(max_length=64)
    message = serializers.CharField()
    session_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
