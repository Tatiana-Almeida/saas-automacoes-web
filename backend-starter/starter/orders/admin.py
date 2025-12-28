from django.contrib import admin

from .models import Cart, CartItem, Order, OrderItem, PaymentTransaction


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("unit_price", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total", "status", "ordered_at")
    list_filter = ("status",)
    search_fields = ("user__email",)
    readonly_fields = ("total", "ordered_at", "updated_at")
    inlines = [OrderItemInline]


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("unit_price", "line_total")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    search_fields = ("user__email",)
    inlines = [CartItemInline]


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "provider", "status", "amount", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("order__id", "order__user__email", "reference")
    readonly_fields = (
        "status",
        "reference",
        "message",
        "payload",
        "created_at",
        "updated_at",
    )
