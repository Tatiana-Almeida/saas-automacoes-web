from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .emails import send_password_reset_email, send_verification_email
from .serializers import (
    ChangePasswordSerializer,
    ConfirmEmailSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
)
from .tokens import blacklist_refresh_token, is_token_blacklisted

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        out = ser.save()
        # send email (uses locmem in tests)
        send_verification_email(out["user"], out["token"])
        return Response(
            {"id": out["user"].pk, "email": out["user"].email},
            status=status.HTTP_201_CREATED,
        )


class ConfirmEmailView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        ser = ConfirmEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response({"id": user.pk, "email": user.email})


class LoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # Basic brute-force protection: track failed attempts per email
        email = request.data.get("email", "")
        cache_key = f"login_fail:{email.lower()}"
        fails = cache.get(cache_key, 0)
        if fails >= getattr(settings, "LOGIN_FAIL_LIMIT", 5):
            return Response(
                {"detail": "Too many attempts"},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        # reset fail counter on success
        cache.delete(cache_key)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Missing refresh token"}, status=status.HTTP_400_BAD_REQUEST
            )
        ok = blacklist_refresh_token(refresh_token)
        if not ok:
            return Response(
                {"detail": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TokenRefreshView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Missing refresh token"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            rt = RefreshToken(refresh_token)
            jti = rt.get("jti")
            if is_token_blacklisted(jti):
                return Response(
                    {"detail": "Token revoked"}, status=status.HTTP_401_UNAUTHORIZED
                )
            # issue new tokens
            user = User.objects.get(pk=rt["user_id"])
            new_rt = RefreshToken.for_user(user)
            return Response(
                {"access": str(new_rt.access_token), "refresh": str(new_rt)}
            )
        except Exception:
            return Response(
                {"detail": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST
            )


class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        out = ser.save()
        send_password_reset_email(out["user"], out["token"])
        return Response({"detail": "sent"})


class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response({"id": user.pk})


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return ProfileUpdateSerializer
        return ProfileSerializer


class ChangePasswordView(generics.GenericAPIView):
    # allow Any and handle auth via refresh token or session inside the view
    permission_classes = [permissions.AllowAny]
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)

        user = None
        # prefer authenticated user
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            # try identifying user via provided refresh token
            refresh_token = ser.validated_data.get("refresh")
            if refresh_token:
                try:
                    rt = RefreshToken(refresh_token)
                    user = User.objects.get(pk=rt["user_id"])
                except Exception:
                    return Response(
                        {"detail": "Invalid refresh token"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        if user is None:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(ser.validated_data["current_password"]):
            # increment fail counter
            email = user.email or ""
            cache_key = f"login_fail:{email.lower()}"
            cache.incr(cache_key)
            cache.expire(cache_key, getattr(settings, "LOGIN_FAIL_WINDOW", 300))
            return Response(
                {"detail": "Current password incorrect"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # set new password
        user.set_password(ser.validated_data["new_password"])
        user.save()
        # optionally blacklist provided refresh token
        refresh = ser.validated_data.get("refresh")
        if refresh:
            blacklist_refresh_token(refresh)
        return Response({"detail": "password_changed"})
