from decouple import config
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from ..serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "refresh token é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {"detail": "token inválido"}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {"detail": "logout efetuado"}, status=status.HTTP_205_RESET_CONTENT
        )


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        result = serializer.save()
        # Send email if uid/token provided
        uid = result.get("uid")
        token = result.get("token")
        if uid and token:
            reset_url = request.data.get("reset_base_url") or config(
                "PASSWORD_RESET_BASE_URL", default=""
            )
            context = {
                "uid": uid,
                "token": token,
                "reset_url": reset_url,
                "site_name": config("SITE_NAME", default="SaaS"),
            }
            text_message = render_to_string("emails/password_reset.txt", context)
            html_message = render_to_string("emails/password_reset.html", context)
            subject = "Recuperação de senha"
            from_email = config("DEFAULT_FROM_EMAIL", default=None)
            to = [request.data.get("email")]
            try:
                msg = EmailMultiAlternatives(subject, text_message, from_email, to)
                msg.attach_alternative(html_message, "text/html")
                msg.send(fail_silently=True)
            except Exception:
                # Fallback to plain text
                send_mail(subject, text_message, from_email, to, fail_silently=True)
        return Response({"sent": True})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "senha atualizada"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
