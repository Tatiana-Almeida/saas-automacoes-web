from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .emails import send_verification_email
from .models import EmailVerificationToken, PasswordResetToken

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    nome_completo = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email já registado")
        return value.lower()

    def validate(self, data):
        if data.get("password") != data.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match"}
            )
        validate_password(data.get("password"))
        return data

    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data["email"],
            is_active=False,
            **(
                {"nome_completo": validated_data.get("nome_completo")}
                if validated_data.get("nome_completo")
                else {}
            ),
        )
        user.set_password(validated_data["password"])
        user.save()
        token = EmailVerificationToken.objects.create(user=user)
        return {"user": user, "token": token}


class ConfirmEmailSerializer(serializers.Serializer):
    token = serializers.UUIDField()

    def validate_token(self, value):
        try:
            t = EmailVerificationToken.objects.get(token=value)
        except EmailVerificationToken.DoesNotExist:
            raise serializers.ValidationError("Invalid token")
        if t.used:
            raise serializers.ValidationError("Token already used")
        if t.is_expired():
            raise serializers.ValidationError("Token expired")
        self.instance = t
        return value

    def save(self):
        t: EmailVerificationToken = self.instance
        user = t.user
        user.is_active = True
        user.save(update_fields=["is_active"])
        t.mark_used()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data.get("email"), password=data.get("password"))
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError("Account not activated")
        data["user"] = user
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email__iexact=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user with this email")
        self.user = user
        return value

    def save(self):
        token = PasswordResetToken.objects.create(user=self.user)
        return {"user": self.user, "token": token}


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data.get("new_password") != data.get("new_password_confirm"):
            raise serializers.ValidationError("Passwords do not match")
        validate_password(data.get("new_password"))
        try:
            t = PasswordResetToken.objects.get(token=data.get("token"))
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({"token": "Invalid token"})
        if t.used or t.is_expired():
            raise serializers.ValidationError({"token": "Token invalid or expired"})
        self.instance = t
        return data

    def save(self):
        t: PasswordResetToken = self.instance
        user = t.user
        user.set_password(self.validated_data["new_password"])
        user.save()
        t.mark_used()
        return user


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "nome_completo")
        read_only_fields = ("id",)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "nome_completo")

    def update(self, instance, validated_data):
        new_email = validated_data.get("email")
        if new_email and new_email.lower() != instance.email.lower():
            instance.email = new_email.lower()
            instance.is_active = False
            instance.save(update_fields=["email", "is_active"])
            # create verification token and send verification email
            token = EmailVerificationToken.objects.create(user=instance)
            try:
                send_verification_email(instance, token)
            except Exception:
                pass
            return instance
        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)
    refresh = serializers.CharField(write_only=True, required=False)

    def validate(self, data):
        if data.get("new_password") != data.get("new_password_confirm"):
            raise serializers.ValidationError("Passwords do not match")
        validate_password(data.get("new_password"))
        return data
