from rest_framework import serializers

from ..models import Category, Product, Tag


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "is_active")
        read_only_fields = ("id", "slug")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug", "is_active")
        read_only_fields = ("id", "slug")


class ProductSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)
    image_thumb = serializers.ImageField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "image",
            "image_thumb",
            "price",
            "is_active",
            "categories",
            "tags",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "created_at", "updated_at")


class ProductWriteSerializer(serializers.ModelSerializer):
    # Allow writing relations by ids
    category_ids = serializers.PrimaryKeyRelatedField(
        source="categories", many=True, queryset=Category.objects.all(), required=False
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        source="tags", many=True, queryset=Tag.objects.all(), required=False
    )

    class Meta:
        model = Product
        fields = (
            "name",
            "description",
            "image",
            "price",
            "is_active",
            "category_ids",
            "tag_ids",
        )
