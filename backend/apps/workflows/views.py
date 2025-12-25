from rest_framework.permissions import IsAuthenticated
from apps.rbac.permissions import HasPermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from .serializers import WorkflowExecuteSerializer
from .tasks import execute_workflow


class WorkflowsStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Workflows service status",
        description="Returns current Workflows module status",
        responses={200: None},
        examples=[OpenApiExample("ok", value={"service": "workflows", "status": "ok"})],
        tags=["workflows"],
    )
    def get(self, request):
        return Response({"service": "workflows", "status": "ok"})


class WorkflowExecuteView(APIView):
    required_permission = "workflows_execute"
    permission_classes = [IsAuthenticated, HasPermission]
    throttle_scope = "workflows_execute"

    @extend_schema(
        summary="Execute workflow",
        description="Triggers execution of a workflow with input payload. Rate limited according to tenant plan.",
        request=WorkflowExecuteSerializer,
        responses={
            201: OpenApiExample(
                "accepted", value={"id": "wfexec_123", "status": "queued"}
            )
        },
        tags=["workflows"],
    )
    @swagger_auto_schema(
        operation_summary="Execute workflow",
        request_body=WorkflowExecuteSerializer,
        responses={
            201: openapi.Response(
                description="Workflow execution queued",
                examples={"application/json": {"id": "wfexec_123", "status": "queued"}},
            )
        },
        tags=["workflows"],
    )
    def post(self, request):
        serializer = WorkflowExecuteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        task = execute_workflow.delay(data["workflow_id"], data.get("input"))
        return Response(
            {"id": task.id, "status": "queued"}, status=status.HTTP_201_CREATED
        )
