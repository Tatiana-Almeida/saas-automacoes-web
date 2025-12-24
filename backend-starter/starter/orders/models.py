from django.conf import settings
from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator
from starter.products.models import Product


class OrderStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PAID = 'paid', 'Paid'
    CANCELED = 'canceled', 'Canceled'


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    ordered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-ordered_at",)

    def __str__(self) -> str:
        return f"Order #{self.pk} - {self.user}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    line_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.price
        self.line_total = (self.unit_price or Decimal('0')) * Decimal(self.quantity or 0)
        super().save(*args, **kwargs)


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Cart for {self.user}"

    @property
    def total(self) -> Decimal:
        return sum((item.line_total for item in self.items.all()), Decimal('0'))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    line_total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])

    class Meta:
        unique_together = ('cart', 'product')

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.price
        self.line_total = (self.unit_price or Decimal('0')) * Decimal(self.quantity or 0)
        super().save(*args, **kwargs)


class PaymentProvider(models.TextChoices):
    LOCAL = 'local', 'Local Simulator'
    STRIPE = 'stripe', 'Stripe'
    PAYPAL = 'paypal', 'PayPal'


class PaymentStatus(models.TextChoices):
    INITIATED = 'initiated', 'Initiated'
    SUCCEEDED = 'succeeded', 'Succeeded'
    FAILED = 'failed', 'Failed'


class PaymentTransaction(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    provider = models.CharField(max_length=20, choices=PaymentProvider.choices, default=PaymentProvider.LOCAL)
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.INITIATED)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    reference = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    payload = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f"Payment {self.provider} {self.status} for Order #{self.order_id}"
