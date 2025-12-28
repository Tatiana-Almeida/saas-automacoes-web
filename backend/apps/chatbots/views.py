from apps.rbac.permissions import HasPermission
from drf_spectacular.utils import OpenApiExample, extend_schema
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ChatbotMessageSerializer
from .tasks import send_chatbot_message


class ChatbotsStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Chatbots service status",
        description="Returns current Chatbots module status",
        responses={200: None},
        examples=[OpenApiExample("ok", value={"service": "chatbots", "status": "ok"})],
        tags=["chatbots"],
    )
    def get(self, request):
        return Response({"service": "chatbots", "status": "ok"})


class ChatbotSendMessageView(APIView):
    required_permission = "chatbots_send"
    permission_classes = [IsAuthenticated, HasPermission]
    throttle_scope = "chatbots_send"

    @extend_schema(
        summary="Send message to chatbot",
        description="Sends a message to a chatbot and enqueues processing. Rate limited per tenant plan.",
        request=ChatbotMessageSerializer,
        responses={
            201: OpenApiExample(
                "accepted", value={"id": "chatmsg_123", "status": "queued"}
            )
        },
        tags=["chatbots"],
    )
    @swagger_auto_schema(
        operation_summary="Send message to chatbot",
        request_body=ChatbotMessageSerializer,
        responses={
            201: openapi.Response(
                description="Chatbot message queued",
                examples={
                    "application/json": {"id": "chatmsg_123", "status": "queued"}
                },
            )
        },
        tags=["chatbots"],
    )
    def post(self, request):
        serializer = ChatbotMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        task = send_chatbot_message.delay(
            data["bot_id"], data["message"], data.get("session_id")
        )
        return Response(
            {"id": task.id, "status": "queued"}, status=status.HTTP_201_CREATED
        )
