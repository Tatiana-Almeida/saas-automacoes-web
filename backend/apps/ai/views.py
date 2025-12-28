from apps.rbac.permissions import HasPermission
from drf_spectacular.utils import OpenApiExample, extend_schema
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AiInferSerializer
from .tasks import run_ai_inference


class AiStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="AI service status",
        description="Returns current AI module status",
        responses={200: None},
        examples=[OpenApiExample("ok", value={"service": "ai", "status": "ok"})],
        tags=["ai"],
    )
    def get(self, request):
        return Response({"service": "ai", "status": "ok"})


class AiInferView(APIView):
    required_permission = "ai_infer"
    permission_classes = [IsAuthenticated, HasPermission]
    throttle_scope = "ai_infer"

    @extend_schema(
        summary="AI inference",
        description="Submits a prompt to a model for inference. Rate limited based on tenant plan.",
        request=AiInferSerializer,
        responses={
            201: OpenApiExample(
                "accepted", value={"id": "infer_123", "status": "queued"}
            )
        },
        tags=["ai"],
    )
    @swagger_auto_schema(
        operation_summary="AI inference",
        request_body=AiInferSerializer,
        responses={
            201: openapi.Response(
                description="Inference queued",
                examples={"application/json": {"id": "infer_123", "status": "queued"}},
            )
        },
        tags=["ai"],
    )
    def post(self, request):
        serializer = AiInferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        task = run_ai_inference.delay(data["model"], data["prompt"])
        return Response(
            {"id": task.id, "status": "queued"}, status=status.HTTP_201_CREATED
        )
