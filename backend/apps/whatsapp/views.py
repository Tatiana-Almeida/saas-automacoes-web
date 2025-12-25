from rest_framework.permissions import IsAuthenticated
from apps.rbac.permissions import HasPermission
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from .serializers import WhatsappSendSerializer
from .tasks import send_whatsapp_message


class WhatsappStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="WhatsApp service status",
        description="Returns current WhatsApp module status",
        responses={200: None},
        examples=[OpenApiExample("ok", value={"service": "whatsapp", "status": "ok"})],
        tags=["whatsapp"],
    )
    def get(self, request):
        return Response({"service": "whatsapp", "status": "ok"})


class WhatsappSendMessageView(APIView):
    required_permission = "send_whatsapp"
    permission_classes = [IsAuthenticated, HasPermission]
    throttle_scope = "send_whatsapp"

    @extend_schema(
        summary="Send WhatsApp message",
        request=WhatsappSendSerializer,
        responses={201: None},
        examples=[
            OpenApiExample("send", value={"to": "+351900000000", "message": "Olá!"})
        ],
        tags=["whatsapp"],
    )
    @swagger_auto_schema(
        operation_summary="Send WhatsApp message",
        request_body=WhatsappSendSerializer,
        responses={
            201: openapi.Response(
                description="Message queued",
                examples={
                    "application/json": {
                        "queued": True,
                        "to": "+351900000000",
                        "task_id": "celery-task-id",
                    }
                },
            )
        },
        tags=["whatsapp"],
    )
    def post(self, request):
        serializer = WhatsappSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        task = send_whatsapp_message.delay(data["to"], data["message"])
        return Response(
            {"queued": True, "to": data["to"], "task_id": task.id},
            status=status.HTTP_201_CREATED,
        )
