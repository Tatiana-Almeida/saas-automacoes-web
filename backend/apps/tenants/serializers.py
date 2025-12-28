from rest_framework import serializers

from .models import Domain, Tenant


class TenantCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    schema_name = serializers.RegexField(regex=r"^[a-z0-9_]+$", max_length=63)
    domain = serializers.CharField(max_length=255)
    plan = serializers.CharField(max_length=50, required=False, default="free")

    def validate_schema_name(self, value):
        if value in ("public",):
            raise serializers.ValidationError("schema_name inválido")
        return value

    def create(self, validated_data):
        name = validated_data["name"]
        schema_name = validated_data["schema_name"]
        domain_name = validated_data["domain"]
        plan = validated_data.get("plan", "free")

        tenant = Tenant(name=name, schema_name=schema_name, plan=plan, is_active=True)
        tenant.save()  # auto_create_schema criará o schema

        Domain.objects.create(domain=domain_name, tenant=tenant, is_primary=True)
        return tenant


class TenantActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["suspend", "reactivate"])


class TenantPlanUpdateSerializer(serializers.Serializer):
    plan = serializers.CharField(max_length=50)

    def validate_plan(self, value):
        # Ensure plan exists
        from .models import Plan

        try:
            Plan.objects.get(code=value)
        except Plan.DoesNotExist:
            raise serializers.ValidationError("Plano não encontrado")
        return value
