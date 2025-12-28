from rest_framework import serializers


class AiInferSerializer(serializers.Serializer):
    model = serializers.CharField(max_length=100)
    prompt = serializers.CharField()
