from rest_framework import serializers


class SmsSendSerializer(serializers.Serializer):
    to = serializers.CharField(max_length=20)
    message = serializers.CharField(max_length=500)
