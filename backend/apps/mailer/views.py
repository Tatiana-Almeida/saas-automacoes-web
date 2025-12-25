from rest_framework.permissions import IsAuthenticated
from apps.rbac.permissions import HasPermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from .serializers import EmailSendSerializer
from .tasks import send_email_message


class MailerStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Email service status",
        description="Returns current Email/Mailer module status",
        responses={200: None},
        examples=[OpenApiExample("ok", value={"service": "mailer", "status": "ok"})],
        tags=["email"],
    )
    def get(self, request):
        return Response({"service": "mailer", "status": "ok"})


class MailerSendEmailView(APIView):
    required_permission = "email_send"
    permission_classes = [IsAuthenticated, HasPermission]
    throttle_scope = "email_send"

    @extend_schema(
        summary="Send email",
        description="Queues an email to be sent",
        request=EmailSendSerializer,
        responses={
            201: OpenApiExample("queued", value={"id": "email_123", "status": "queued"})
        },
        tags=["email"],
    )
    @swagger_auto_schema(
        operation_summary="Send email",
        request_body=EmailSendSerializer,
        responses={
            201: openapi.Response(
                description="Email queued",
                examples={"application/json": {"id": "email_123", "status": "queued"}},
            )
        },
        tags=["email"],
    )
    def post(self, request):
        serializer = EmailSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = send_email_message.delay(
            serializer.validated_data["to"],
            serializer.validated_data["subject"],
            serializer.validated_data["body"],
        )
        return Response(
            {"id": task.id, "status": "queued"}, status=status.HTTP_201_CREATED
        )
