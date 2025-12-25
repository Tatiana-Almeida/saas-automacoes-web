from rest_framework import serializers


class WhatsappSendSerializer(serializers.Serializer):
    to = serializers.CharField(max_length=32)
    message = serializers.CharField(max_length=2000)
