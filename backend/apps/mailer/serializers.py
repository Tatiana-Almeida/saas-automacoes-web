from rest_framework import serializers


class EmailSendSerializer(serializers.Serializer):
    to = serializers.EmailField()
    subject = serializers.CharField(max_length=200)
    body = serializers.CharField()
