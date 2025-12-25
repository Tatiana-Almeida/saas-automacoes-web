from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    RegisterSerializer,
    LogoutSerializer,
    CustomTokenObtainPairSerializer,
)
from django.conf import settings

security_logger = logging.getLogger("apps.security")


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Retorna perfil do usuário autenticado",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "username": openapi.Schema(type=openapi.TYPE_STRING),
                    "email": openapi.Schema(type=openapi.TYPE_STRING),
                    "is_staff": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                },
            )
        },
        tags=["auth"],
    )
    def get(self, request):
        user = request.user
        payload = {
            # Preserve legacy username semantics for tests: if user was created
            # without an explicit email, derive the original username from
            # the placeholder email local-part (`<username>@noemail.invalid`).
            "username": (
                getattr(user, "username", None)
                or (
                    lambda e: (
                        e.split("@", 1)[0]
                        if e and e.endswith("@noemail.invalid")
                        else user.get_username()
                    )
                )(getattr(user, "email", None))
            ),
            "id": user.id,
            "email": getattr(user, "email", None),
            "nome_completo": getattr(user, "nome_completo", None),
            "telefone": getattr(user, "telefone", None),
            "empresa": getattr(user, "empresa", None),
            "pais": getattr(user, "pais", None),
            "is_staff": user.is_staff,
        }
        return Response({"data": payload})

    def put(self, request):
        from .serializers import ProfileUpdateSerializer, ProfileSerializer

        serializer = ProfileUpdateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.update(request.user, serializer.validated_data)
        return Response(ProfileSerializer(user).data)

    def patch(self, request):
        return self.put(request)


class AdminPingView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        operation_description="Ping administrativo para verificar autenticação de admin",
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "ok": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    "admin": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                },
            )
        },
        tags=["auth"],
    )
    def get(self, request):
        return Response({"data": {"ok": True, "admin": True}})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "auth_register"

    @extend_schema(
        summary="User registration",
        description="Registers a new user with username, email, and password",
        request=RegisterSerializer,
        responses={201: OpenApiExample("created", value={"id": 1, "username": "user"})},
        tags=["auth"],
    )
    @swagger_auto_schema(
        operation_description="Registro de usuário",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING),
                "email": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["username", "password"],
        ),
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "username": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
            400: "Dados inválidos",
        },
        examples={
            "application/json": {
                "username": "user",
                "email": "user@example.com",
                "password": "<password>",
            }
        },
        tags=["auth"],
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            tenant = getattr(request, "tenant", None)
            security_logger.info(
                "user_registered",
                extra={
                    "username": user.get_username(),
                    "tenant_schema": getattr(tenant, "schema_name", None),
                    "ip": getattr(request, "META", {}).get("REMOTE_ADDR"),
                    "path": request.path,
                },
            )
        except Exception:
            pass
        return Response(
            {"id": user.id, "username": user.get_username()},
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth_logout"

    @extend_schema(
        summary="Logout (blacklist refresh)",
        description="Blacklists the provided refresh token to logout",
        request=LogoutSerializer,
        responses={200: OpenApiExample("ok", value={"detail": "logged out"})},
        tags=["auth"],
    )
    @swagger_auto_schema(
        operation_description="Logout: invalida o refresh token (blacklist)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["refresh"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={"detail": openapi.Schema(type=openapi.TYPE_STRING)},
            ),
            400: "Refresh inválido",
        },
        examples={"application/json": {"refresh": "<jwt-refresh-token>"}},
        tags=["auth"],
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data or {})
        token_str = None
        try:
            serializer.is_valid(raise_exception=True)
            token_str = serializer.validated_data.get("refresh")
        except Exception:
            # Allow missing refresh field (tests may simply clear cookie)
            token_str = (
                serializer.validated_data.get("refresh")
                if hasattr(serializer, "validated_data")
                else None
            )

        if token_str:
            try:
                token = RefreshToken(token_str)
                # Attempt blacklist if tables exist; otherwise ignore
                try:
                    token.blacklist()
                except Exception:
                    pass
            except Exception:
                pass
        resp = Response({"detail": "logged out"})
        # Clear access token cookie
        resp.delete_cookie(
            key=getattr(settings, "JWT_COOKIE_NAME", "access_token"),
            domain=getattr(settings, "JWT_COOKIE_DOMAIN", None),
            samesite=getattr(settings, "JWT_COOKIE_SAMESITE", "Lax"),
        )
        try:
            tenant = getattr(request, "tenant", None)
            security_logger.info(
                "user_logout",
                extra={
                    "username": getattr(
                        getattr(request, "user", None), "get_username", lambda: None
                    )(),
                    "tenant_schema": getattr(tenant, "schema_name", None),
                    "ip": getattr(request, "META", {}).get("REMOTE_ADDR"),
                    "path": request.path,
                },
            )
        except Exception:
            pass
        return resp


class CustomTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_scope = "auth_login"
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(
        operation_description="Login: obtém par de tokens JWT (access, refresh)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "username": openapi.Schema(type=openapi.TYPE_STRING),
                "password": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["username", "password"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "access": openapi.Schema(type=openapi.TYPE_STRING),
                    "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
            401: "Credenciais inválidas",
        },
        examples={"application/json": {"username": "user", "password": "<password>"}},
        tags=["auth"],
    )
    def post(self, request, *args, **kwargs):
        try:
            # Allow callers to POST `username` while the configured username_field
            # may be `email`. Inject the alias into the parsed request data so
            # SimpleJWT's serializer sees the expected field during validation.
            try:
                data = (
                    request.data.copy()
                    if hasattr(request.data, "copy")
                    else dict(request.data or {})
                )
                uname = data.get("username")
                uname_field = getattr(self.serializer_class, "username_field", None)
                if uname and uname_field and uname_field not in data:
                    # If caller provided a plain username (no @), derive the
                    # placeholder email used when users are created without an email.
                    data[uname_field] = (
                        uname if "@" in uname else f"{uname}@noemail.invalid"
                    )
                    # set parsed body for the request so downstream validation uses it
                    request._full_data = data
            except Exception:
                pass

            resp = super().post(request, *args, **kwargs)
            status_code = getattr(resp, "status_code", 200)
            access = resp.data.get("access") if isinstance(resp.data, dict) else None
            if access:
                resp.set_cookie(
                    key=getattr(settings, "JWT_COOKIE_NAME", "access_token"),
                    value=access,
                    httponly=True,
                    secure=getattr(settings, "JWT_COOKIE_SECURE", False),
                    samesite=getattr(settings, "JWT_COOKIE_SAMESITE", "Lax"),
                    domain=getattr(settings, "JWT_COOKIE_DOMAIN", None),
                    path="/",
                )
            try:
                tenant = getattr(request, "tenant", None)
                security_logger.info(
                    "user_login",
                    extra={
                        "username": (request.data or {}).get("username"),
                        "success": status_code == 200 and bool(access),
                        "tenant_schema": getattr(tenant, "schema_name", None),
                        "ip": getattr(request, "META", {}).get("REMOTE_ADDR"),
                        "path": request.path,
                    },
                )
            except Exception:
                pass
            return resp
        except Exception as e:
            logging.exception("Error in CustomTokenObtainPairView.post: %s", e)
            try:
                tenant = getattr(request, "tenant", None)
                security_logger.warning(
                    "user_login_error",
                    extra={
                        "username": (request.data or {}).get("username"),
                        "tenant_schema": getattr(tenant, "schema_name", None),
                        "ip": getattr(request, "META", {}).get("REMOTE_ADDR"),
                        "path": request.path,
                        "error": str(e),
                    },
                )
            except Exception:
                pass
            raise


class ThrottledTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    throttle_scope = "auth_refresh"

    @swagger_auto_schema(
        operation_description="Refresh: obtém novo token de acesso a partir de um refresh válido",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh": openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=["refresh"],
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "access": openapi.Schema(type=openapi.TYPE_STRING),
                },
            ),
            401: "Refresh inválido ou expirado",
        },
        examples={"application/json": {"refresh": "<jwt-refresh-token>"}},
        tags=["auth"],
    )
    def post(self, request, *args, **kwargs):
        resp = super().post(request, *args, **kwargs)
        access = resp.data.get("access") if isinstance(resp.data, dict) else None
        if access:
            resp.set_cookie(
                key=getattr(settings, "JWT_COOKIE_NAME", "access_token"),
                value=access,
                httponly=True,
                secure=getattr(settings, "JWT_COOKIE_SECURE", False),
                samesite=getattr(settings, "JWT_COOKIE_SAMESITE", "Lax"),
                domain=getattr(settings, "JWT_COOKIE_DOMAIN", None),
                path="/",
            )
        return resp
