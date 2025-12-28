from rest_framework import serializers


class WorkflowExecuteSerializer(serializers.Serializer):
    workflow_id = serializers.CharField(max_length=64)
    input = serializers.JSONField(required=False)
