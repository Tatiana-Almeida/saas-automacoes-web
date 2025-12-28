import logging
from decimal import Decimal
from typing import Tuple

from django.db import transaction

from ..models import (
    Order,
    OrderStatus,
    PaymentProvider,
    PaymentStatus,
    PaymentTransaction,
)

logger = logging.getLogger(__name__)


class PaymentService:
    """Base payment service for processing payments"""

    @staticmethod
    def process_payment(order: Order, provider: str) -> Tuple[PaymentTransaction, bool]:
        """
        Process payment for an order.
        Returns (payment_transaction, success: bool)
        """
        payment = PaymentTransaction.objects.create(
            order=order,
            provider=provider,
            status=PaymentStatus.INITIATED,
            amount=order.total,
        )

        try:
            if provider == PaymentProvider.LOCAL:
                return PaymentService._process_local(payment, order)
            elif provider == PaymentProvider.STRIPE:
                return PaymentService._process_stripe(payment, order)
            elif provider == PaymentProvider.PAYPAL:
                return PaymentService._process_paypal(payment, order)
            else:
                payment.status = PaymentStatus.FAILED
                payment.message = f"Provider não suportado: {provider}"
                payment.save()
                logger.error(f"Unsupported provider {provider} for order {order.id}")
                return payment, False
        except Exception as e:
            payment.status = PaymentStatus.FAILED
            payment.message = f"Erro no processamento: {str(e)}"
            payment.save()
            logger.exception(f"Payment processing failed for order {order.id}")
            return payment, False

    @staticmethod
    @transaction.atomic
    def _process_local(
        payment: PaymentTransaction, order: Order
    ) -> Tuple[PaymentTransaction, bool]:
        """Local simulator: success if total > 0"""
        if order.total > Decimal("0"):
            payment.status = PaymentStatus.SUCCEEDED
            payment.reference = f"LOCAL-{order.id}"
            payment.message = "Pagamento aprovado (simulado)"
            order.status = OrderStatus.PAID
            payment.save()
            order.save()
            logger.info(f"Local payment succeeded for order {order.id}")
            return payment, True
        else:
            payment.status = PaymentStatus.FAILED
            payment.message = "Pagamento falhou: total inválido"
            order.status = OrderStatus.CANCELED
            payment.save()
            order.save()
            logger.warning(f"Local payment failed for order {order.id}: invalid total")
            return payment, False

    @staticmethod
    @transaction.atomic
    def _process_stripe(
        payment: PaymentTransaction, order: Order
    ) -> Tuple[PaymentTransaction, bool]:
        """
        Stripe integration placeholder.
        Replace with actual Stripe API calls.
        """
        # TODO: Integrate with Stripe API
        # import stripe
        # stripe.api_key = settings.STRIPE_SECRET_KEY
        # intent = stripe.PaymentIntent.create(amount=int(order.total * 100), currency='usd', ...)
        # payment.reference = intent.id

        # For now, simulate success
        payment.status = PaymentStatus.SUCCEEDED
        payment.reference = f"STRIPE-SIM-{order.id}"
        payment.message = "Pagamento Stripe (simulado)"
        payment.payload = {"simulated": True}
        order.status = OrderStatus.PAID
        payment.save()
        order.save()
        logger.info(f"Stripe payment simulated for order {order.id}")
        return payment, True

    @staticmethod
    @transaction.atomic
    def _process_paypal(
        payment: PaymentTransaction, order: Order
    ) -> Tuple[PaymentTransaction, bool]:
        """
        PayPal integration placeholder.
        Replace with actual PayPal API calls.
        """
        # TODO: Integrate with PayPal SDK
        # Configure PayPal and create order via API

        # For now, simulate success
        payment.status = PaymentStatus.SUCCEEDED
        payment.reference = f"PAYPAL-SIM-{order.id}"
        payment.message = "Pagamento PayPal (simulado)"
        payment.payload = {"simulated": True}
        order.status = OrderStatus.PAID
        payment.save()
        order.save()
        logger.info(f"PayPal payment simulated for order {order.id}")
        return payment, True

    @staticmethod
    @transaction.atomic
    def handle_webhook(provider: str, payload: dict) -> bool:
        """
        Handle payment provider webhooks.
        Returns True if processed successfully.
        """
        try:
            if provider == PaymentProvider.STRIPE:
                return PaymentService._handle_stripe_webhook(payload)
            elif provider == PaymentProvider.PAYPAL:
                return PaymentService._handle_paypal_webhook(payload)
            else:
                logger.warning(
                    f"Webhook received from unsupported provider: {provider}"
                )
                return False
        except Exception:
            logger.exception(f"Webhook processing failed for {provider}")
            return False

    @staticmethod
    def _handle_stripe_webhook(payload: dict) -> bool:
        """Handle Stripe webhook events"""
        # TODO: Verify signature and process events
        # event_type = payload.get('type')
        # if event_type == 'payment_intent.succeeded':
        #     payment_intent = payload['data']['object']
        #     reference = payment_intent['id']
        #     payment = PaymentTransaction.objects.get(reference=reference)
        #     payment.status = PaymentStatus.SUCCEEDED
        #     payment.order.status = OrderStatus.PAID
        #     payment.save()
        #     payment.order.save()
        logger.info("Stripe webhook received (placeholder)")
        return True

    @staticmethod
    def _handle_paypal_webhook(payload: dict) -> bool:
        """Handle PayPal webhook events"""
        # TODO: Verify signature and process events
        logger.info("PayPal webhook received (placeholder)")
        return True
