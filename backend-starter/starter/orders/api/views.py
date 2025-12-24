from django.db import transaction
from decimal import Decimal
import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from ..models import Order, OrderItem, Cart, CartItem, PaymentTransaction, PaymentStatus, PaymentProvider, OrderStatus
from .serializers import (
    OrderSerializer,
    CartSerializer,
    CartItemSerializer,
    AddCartItemSerializer,
    UpdateCartItemSerializer,
    CheckoutSerializer,
    PaymentTransactionSerializer,
)
from ..services import PaymentService
from starter.api.views import TenantScopedViewSet
from starter.api.permissions import IsAdminOrReadOnly

logger = logging.getLogger(__name__)


class OrderViewSet(TenantScopedViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAdminOrReadOnly]


def _get_or_create_cart(user) -> Cart:
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = _get_or_create_cart(request.user)
        return Response(CartSerializer(cart).data)

    def post(self, request):
        cart = _get_or_create_cart(request.user)
        serializer = AddCartItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        item, created = CartItem.objects.get_or_create(cart=cart, product_id=product_id)
        item.quantity = item.quantity + quantity if not created else quantity
        item.save()
        return Response(CartItemSerializer(item).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id: int):
        cart = _get_or_create_cart(request.user)
        try:
            item = cart.items.get(id=item_id)
        except CartItem.DoesNotExist:
            return Response({"detail": "Item não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UpdateCartItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        item.quantity = serializer.validated_data['quantity']
        item.save()
        return Response(CartItemSerializer(item).data)

    def delete(self, request, item_id: int):
        cart = _get_or_create_cart(request.user)
        try:
            item = cart.items.get(id=item_id)
        except CartItem.DoesNotExist:
            return Response({"detail": "Item não encontrado"}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        cart = _get_or_create_cart(request.user)
        if cart.items.count() == 0:
            return Response({"detail": "Carrinho vazio"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = CheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # Create order
        order = Order.objects.create(user=request.user, total=cart.total, status=OrderStatus.PENDING)
        for ci in cart.items.all():
            OrderItem.objects.create(order=order, product=ci.product, quantity=ci.quantity, unit_price=ci.unit_price)
        # clear cart
        cart.items.all().delete()
        # process payment via service
        provider = serializer.validated_data['provider']
        logger.info(f'Processing checkout for order {order.id}, provider: {provider}')
        payment, success = PaymentService.process_payment(order, provider)
        
        if not success:
            logger.warning(f'Payment failed for order {order.id}')
        
        return Response({
            "order": OrderSerializer(order).data,
            "payment": PaymentTransactionSerializer(payment).data,
        }, status=status.HTTP_201_CREATED)


class MyOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by('-ordered_at')
        return Response([OrderSerializer(o).data for o in orders])


class WebhookView(APIView):
    """
    Payment provider webhook endpoint.
    Accepts webhooks from Stripe, PayPal, etc.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        provider = request.data.get('provider') or request.query_params.get('provider', 'stripe')
        payload = request.data
        logger.info(f'Received webhook from {provider}')
        
        success = PaymentService.handle_webhook(provider, payload)
        
        if success:
            return Response({"status": "received"}, status=status.HTTP_200_OK)
        return Response({"status": "error"}, status=status.HTTP_400_BAD_REQUEST)
