import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()
logger = logging.getLogger(__name__)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField()


class PasswordResetRequestView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if user:
            token = PasswordResetTokenGenerator().make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = request.build_absolute_uri(
                f"/api/v1/auth/password-reset/confirm/?uid={uid}&token={token}"
            )
            # Send via mailer app if available, else log
            try:
                from apps.mailer import utils as mailer_utils

                mailer_utils.send_password_reset(email, reset_url)
            except Exception:
                logger.info("Password reset for %s: %s", email, reset_url)
        # Always return 200 to avoid email enumeration
        return Response(
            {"detail": "If an account with that email exists, a reset link was sent."}
        )


class PasswordResetConfirmView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]
        try:
            pk = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=pk)
        except Exception:
            return Response(
                {"detail": "Invalid uid/token"}, status=status.HTTP_400_BAD_REQUEST
            )
        # Check token validity and timestamp
        token_gen = PasswordResetTokenGenerator()
        if not token_gen.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # validate password
        from django.contrib.auth.password_validation import validate_password
        from django.core import exceptions

        try:
            validate_password(new_password, user=user)
        except exceptions.ValidationError as e:
            return Response(
                {"password": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST
            )
        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password has been reset."})
