from rest_framework import serializers
from starter.products.api.serializers import ProductSerializer

from ..models import Cart, CartItem, Order, PaymentTransaction


class OrderSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ("id", "user", "total", "status", "ordered_at", "items")
        read_only_fields = ("id", "ordered_at")

    def get_items(self, obj):
        return [
            {
                "product": ProductSerializer(item.product).data,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "line_total": str(item.line_total),
            }
            for item in obj.items.all()
        ]


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=CartItem._meta.get_field("product").remote_field.model.objects.all(),
        write_only=True,
    )

    class Meta:
        model = CartItem
        fields = ("id", "product", "product_id", "quantity", "unit_price", "line_total")
        read_only_fields = ("id", "unit_price", "line_total")


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "user", "items", "total", "created_at", "updated_at")
        read_only_fields = ("id", "user", "items", "total", "created_at", "updated_at")

    def get_total(self, obj):
        return str(obj.total)


class AddCartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(
        choices=["local", "stripe", "paypal"], default="local"
    )


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = (
            "id",
            "order",
            "provider",
            "status",
            "amount",
            "reference",
            "message",
            "payload",
            "created_at",
        )
        read_only_fields = (
            "id",
            "status",
            "reference",
            "message",
            "payload",
            "created_at",
        )
