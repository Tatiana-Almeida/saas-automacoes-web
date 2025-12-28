from apps.rbac.permissions import HasPermission
from drf_spectacular.utils import OpenApiExample, extend_schema
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SmsSendSerializer
from .tasks import send_sms_message


class SmsStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="SMS service status",
        description="Returns current SMS module status",
        responses={200: None},
        examples=[OpenApiExample("ok", value={"service": "sms", "status": "ok"})],
        tags=["sms"],
    )
    def get(self, request):
        return Response({"service": "sms", "status": "ok"})


class SmsSendMessageView(APIView):
    required_permission = "sms_send"
    permission_classes = [IsAuthenticated, HasPermission]
    throttle_scope = "sms_send"

    @extend_schema(
        summary="Send SMS",
        description="Queues an SMS to be sent. Rate limited according to tenant plan.",
        request=SmsSendSerializer,
        responses={
            201: OpenApiExample("queued", value={"id": "sms_123", "status": "queued"})
        },
        tags=["sms"],
    )
    @swagger_auto_schema(
        operation_summary="Send SMS",
        request_body=SmsSendSerializer,
        responses={
            201: openapi.Response(
                description="SMS queued",
                examples={"application/json": {"id": "sms_123", "status": "queued"}},
            )
        },
        tags=["sms"],
    )
    def post(self, request):
        serializer = SmsSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = send_sms_message.delay(
            serializer.validated_data["to"], serializer.validated_data["message"]
        )
        return Response(
            {"id": task.id, "status": "queued"}, status=status.HTTP_201_CREATED
        )
