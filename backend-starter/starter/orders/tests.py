import secrets

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from starter.orders.models import (
    Cart,
    Order,
    OrderStatus,
    PaymentStatus,
    PaymentTransaction,
)
from starter.products.models import Product

User = get_user_model()


class OrdersFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Generate a non-hardcoded test password to satisfy security scanners
        test_password = secrets.token_urlsafe(16) + "A1!"
        self.user = User.objects.create_user(
            email="user@example.com", password=test_password, role="cliente"
        )
        self.product = Product.objects.create(
            name="Auto001", description="Desc", price="99.90", is_active=True
        )
        # auth
        token_url = reverse("token_obtain_pair")
        res = self.client.post(
            token_url,
            {"email": self.user.email, "password": test_password},
            format="json",
        )
        self.access = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_cart_add_update_remove_and_checkout(self):
        # add item
        add_url = reverse("cart")
        res_add = self.client.post(
            add_url, {"product_id": self.product.id, "quantity": 2}, format="json"
        )
        self.assertIn(res_add.status_code, (200, 201))
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        item = cart.items.first()
        self.assertEqual(item.quantity, 2)
        # update item
        upd_url = reverse("cart-item-detail", kwargs={"item_id": item.id})
        res_upd = self.client.patch(upd_url, {"quantity": 3}, format="json")
        self.assertEqual(res_upd.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)
        # remove item
        res_del = self.client.delete(upd_url)
        self.assertEqual(res_del.status_code, 204)
        # add again and checkout
        self.client.post(
            add_url, {"product_id": self.product.id, "quantity": 1}, format="json"
        )
        checkout_url = reverse("orders-checkout")
        res_chk = self.client.post(checkout_url, {"provider": "local"}, format="json")
        self.assertEqual(res_chk.status_code, 201)
        order_id = res_chk.data["order"]["id"]
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.status, OrderStatus.PAID)
        # verify payment transaction
        payment = PaymentTransaction.objects.get(order=order)
        self.assertEqual(payment.status, PaymentStatus.SUCCEEDED)
        # history
        history_url = reverse("orders-me")
        res_hist = self.client.get(history_url)
        self.assertEqual(res_hist.status_code, 200)
        self.assertTrue(any(o["id"] == order_id for o in res_hist.data))

    def test_checkout_empty_cart_fails(self):
        checkout_url = reverse("orders-checkout")
        res = self.client.post(checkout_url, {"provider": "local"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("Carrinho vazio", str(res.data))

    def test_checkout_with_stripe_provider(self):
        """Test checkout with Stripe provider (simulated)"""
        add_url = reverse("cart")
        self.client.post(
            add_url, {"product_id": self.product.id, "quantity": 1}, format="json"
        )
        checkout_url = reverse("orders-checkout")
        res = self.client.post(checkout_url, {"provider": "stripe"}, format="json")
        self.assertEqual(res.status_code, 201)
        payment = PaymentTransaction.objects.get(order_id=res.data["order"]["id"])
        self.assertEqual(payment.provider, "stripe")
        # Note: actual implementation would redirect or return payment URL

    def test_checkout_with_paypal_provider(self):
        """Test checkout with PayPal provider (simulated)"""
        add_url = reverse("cart")
        self.client.post(
            add_url, {"product_id": self.product.id, "quantity": 1}, format="json"
        )
        checkout_url = reverse("orders-checkout")
        res = self.client.post(checkout_url, {"provider": "paypal"}, format="json")
        self.assertEqual(res.status_code, 201)
        payment = PaymentTransaction.objects.get(order_id=res.data["order"]["id"])
        self.assertEqual(payment.provider, "paypal")

    def test_webhook_endpoint_public(self):
        """Test webhook endpoint accepts unauthenticated requests"""
        self.client.credentials()  # clear auth
        webhook_url = reverse("payment-webhook")
        res = self.client.post(
            webhook_url,
            {"provider": "stripe", "order_id": 999, "status": "succeeded"},
            format="json",
        )
        self.assertIn(
            res.status_code, (200, 400)
        )  # accepts request (may fail validation)

    def test_payment_failure_scenario(self):
        """Test payment failure updates order status correctly"""
        # Create product with zero price to trigger failure in local provider
        free_product = Product.objects.create(
            name="Free", description="Free item", price="0.00", is_active=True
        )
        add_url = reverse("cart")
        self.client.post(
            add_url, {"product_id": free_product.id, "quantity": 1}, format="json"
        )
        checkout_url = reverse("orders-checkout")
        res = self.client.post(checkout_url, {"provider": "local"}, format="json")
        self.assertEqual(res.status_code, 201)
        order = Order.objects.get(id=res.data["order"]["id"])
        # Free orders should fail payment
        self.assertEqual(order.status, OrderStatus.CANCELED)
        payment = PaymentTransaction.objects.get(order=order)
        self.assertEqual(payment.status, PaymentStatus.FAILED)
