from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Role, UserRole

User = get_user_model()


class AssignRoleSerializer(serializers.Serializer):
    role = serializers.CharField(max_length=100)

    def validate(self, attrs):
        role_name = attrs['role']
        try:
            role = Role.objects.get(name=role_name)
        except Role.DoesNotExist:
            raise serializers.ValidationError({'role': 'Role não encontrada'})
        attrs['role_obj'] = role
        return attrs


class UserRoleSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='role.name')

    class Meta:
        model = UserRole
        fields = ['role']


class AssignPermissionSerializer(serializers.Serializer):
    permission = serializers.CharField(max_length=100)

    def validate(self, attrs):
        from .models import Permission
        code = attrs['permission']
        try:
            perm = Permission.objects.get(code=code)
        except Permission.DoesNotExist:
            raise serializers.ValidationError({'permission': 'Permissão não encontrada'})
        attrs['permission_obj'] = perm
        return attrs


class UserPermissionSerializer(serializers.ModelSerializer):
    permission = serializers.CharField(source='permission.code')

    class Meta:
        from .models import UserPermission
        model = UserPermission
        fields = ['permission']


class BulkRbacOperationSerializer(serializers.Serializer):
    assign = serializers.DictField(child=serializers.ListField(), required=False)
    revoke = serializers.DictField(child=serializers.ListField(), required=False)

    def validate(self, attrs):
        # Basic structure validation; detailed object checks happen in view
        for section in ('assign', 'revoke'):
            block = attrs.get(section)
            if block:
                for key in block.keys():
                    if key not in ('roles', 'permissions'):
                        raise serializers.ValidationError({section: f'chave inválida: {key}'})
        return attrs


class RoleSerializer(serializers.ModelSerializer):
    # Field that accepts a list of permission codes on input and returns codes on output
    class PermissionCodesField(serializers.Field):
        def to_representation(self, instance):
            try:
                return list(instance.permissions.values_list('code', flat=True))
            except Exception:
                # if instance is a plain iterable of codes
                try:
                    return list(instance)
                except Exception:
                    return []

        def to_internal_value(self, data):
            if data is None:
                return []
            if not isinstance(data, list):
                raise serializers.ValidationError('permissions must be a list of codes')
            for item in data:
                if not isinstance(item, str):
                    raise serializers.ValidationError('permission codes must be strings')
            return data

    permissions = PermissionCodesField(required=False)

    class Meta:
        model = Role
        fields = ['id', 'name', 'permissions']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import Permission
        model = Permission
        fields = ['id', 'code', 'description']
