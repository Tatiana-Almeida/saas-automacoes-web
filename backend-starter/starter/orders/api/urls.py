from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, CartView, CartItemDetailView, CheckoutView, MyOrdersView, WebhookView


router = DefaultRouter()
router.register(r'api/orders', OrderViewSet, basename='order')


urlpatterns = [
    path('', include(router.urls)),
    path('api/cart', CartView.as_view(), name='cart'),
    path('api/cart/items/<int:item_id>', CartItemDetailView.as_view(), name='cart-item-detail'),
    path('api/orders/checkout', CheckoutView.as_view(), name='orders-checkout'),
    path('api/orders/me', MyOrdersView.as_view(), name='orders-me'),
    path('api/payments/webhook', WebhookView.as_view(), name='payment-webhook'),
]
