from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    nome_completo = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Email já cadastrado')
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def create(self, validated_data):
        email = validated_data.get('email')
        nome = validated_data.get('nome_completo', '')
        password = validated_data['password']
        user = User.objects.create_user(email=email, nome_completo=nome, password=password)
        return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow callers to provide `username` without the configured username_field
        # (which may be `email`) by not requiring the username_field at field validation.
        try:
            if self.username_field in self.fields:
                self.fields[self.username_field].required = False
        except Exception:
            pass
    @classmethod
    def get_token(cls, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        token = RefreshToken()
        token["user_id"] = user.id
        return token

    def validate(self, attrs):
        # Accept `username` as an alias for the configured username_field (often `email`).
        # Also accept an email supplied in the identifier field and map it to the
        # username expected by the parent TokenObtainPairSerializer.
        # Map `username` -> configured username_field if present.
        if 'username' in attrs and self.username_field not in attrs:
            attrs[self.username_field] = attrs.pop('username')

        identifier = attrs.get(self.username_field)
        if identifier and '@' in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
            if user:
                # SimpleJWT expects username field; ensure attrs has correct value
                attrs[self.username_field] = user.get_username() if hasattr(user, 'get_username') else user.email
        return super().validate(attrs)


class ProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    nome_completo = serializers.CharField(read_only=True)
    telefone = serializers.CharField(read_only=True, allow_null=True)
    empresa = serializers.CharField(read_only=True, allow_null=True)
    pais = serializers.CharField(read_only=True, allow_null=True)


class ProfileUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    nome_completo = serializers.CharField(required=False, allow_blank=True)
    telefone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    empresa = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    pais = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(write_only=True, required=False)

    def validate_email(self, value):
        User = get_user_model()
        user = self.context.get('request').user
        if User.objects.filter(email__iexact=value).exclude(pk=getattr(user, 'pk', None)).exists():
            raise serializers.ValidationError('Email já cadastrado')
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except exceptions.ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def update(self, instance, validated_data):
        # update allowed fields
        for field in ('email', 'nome_completo', 'telefone', 'empresa', 'pais'):
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
        instance.save()
        return instance
