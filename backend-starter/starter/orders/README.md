# Orders Module

## Overview
The Orders module provides complete e-commerce functionality including shopping cart management, order processing, and payment integration.

## Features

### 🛒 Shopping Cart
- Add/update/remove items
- Automatic price calculation
- One cart per user
- Persistent across sessions

### 📦 Order Management
- Order creation from cart
- Order status tracking (PENDING → PAID/CANCELED)
- Order history
- Admin order management

### 💳 Payment Processing
- Multiple payment providers:
  - **Local**: Simulated payment for testing
  - **Stripe**: Credit card processing (integration ready)
  - **PayPal**: PayPal checkout (integration ready)
- Transaction logging with full audit trail
- Webhook support for async payment confirmations
- Secure payment flow with atomic transactions

## API Endpoints

### Cart Operations

#### Get Current Cart
```http
GET /api/cart
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "user": 1,
  "items": [
    {
      "id": 1,
      "product": {
        "id": 1,
        "name": "Automação Premium",
        "price": "99.90",
        "image": "/media/products/image.jpg"
      },
      "quantity": 2,
      "unit_price": "99.90",
      "line_total": "199.80"
    }
  ],
  "total": "199.80"
}
```

#### Add Item to Cart
```http
POST /api/cart
Authorization: Bearer {token}
Content-Type: application/json

{
  "product_id": 1,
  "quantity": 2
}
```

#### Update Cart Item
```http
PATCH /api/cart/items/{item_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "quantity": 3
}
```

#### Remove Cart Item
```http
DELETE /api/cart/items/{item_id}
Authorization: Bearer {token}
```

### Order Operations

#### Checkout
```http
POST /api/orders/checkout
Authorization: Bearer {token}
Content-Type: application/json

{
  "provider": "local"  // or "stripe", "paypal"
}
```

**Response:**
```json
{
  "order": {
    "id": 1,
    "user": 1,
    "total": "199.80",
    "status": "PAID",
    "ordered_at": "2024-01-15T10:30:00Z",
    "items": [...]
  },
  "payment": {
    "id": 1,
    "provider": "local",
    "status": "SUCCEEDED",
    "amount": "199.80",
    "reference": "local_123456",
    "message": "Pagamento aprovado (simulado)"
  }
}
```

#### Get My Orders
```http
GET /api/orders/me
Authorization: Bearer {token}
```

### Webhooks

#### Payment Webhook (Public)
```http
POST /api/payments/webhook
Content-Type: application/json

{
  "provider": "stripe",
  "order_id": 1,
  "status": "succeeded",
  "reference": "pi_123456",
  "amount": 199.80
}
```

## Models

### Cart
- One-to-one relationship with User
- Automatic total calculation
- Timestamps for tracking

### CartItem
- Links Product to Cart
- Stores quantity and unit price snapshot
- Unique constraint on cart+product

### Order
- User foreign key
- Total amount
- Status: PENDING, PAID, CANCELED
- Timestamp for order placement

### OrderItem
- Order line item
- Product snapshot (name, price)
- Quantity and line total

### PaymentTransaction
- Payment attempt logging
- Provider tracking (local/stripe/paypal)
- Status tracking (INITIATED/SUCCEEDED/FAILED)
- Reference ID for provider transaction
- Full payload storage for debugging
- Error messages

## Payment Service

The `PaymentService` class provides abstraction for payment processing:

```python
from starter.orders.services import PaymentService

# Process payment
payment, success = PaymentService.process_payment(order, provider='stripe')

# Handle webhook
success = PaymentService.handle_webhook(provider='stripe', payload=data)
```

### Supported Providers

#### Local (Simulator)
- Instant payment approval for testing
- Fails if order total is 0
- No external API calls

#### Stripe (Ready for Integration)
```python
# TODO: Add Stripe API implementation
# Set STRIPE_SECRET_KEY in .env
# Install: pip install stripe
```

#### PayPal (Ready for Integration)
```python
# TODO: Add PayPal SDK implementation
# Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in .env
# Install: pip install paypalrestsdk
```

## Security

- All cart/order endpoints require authentication
- Orders are user-scoped (users can only access their own)
- Webhook endpoint is public but should verify signatures (TODO)
- Payment transactions logged with full audit trail
- Atomic database transactions for checkout flow

## Testing

Run tests with:
```bash
python manage.py test starter.orders
```

Test coverage includes:
- ✅ Cart add/update/remove operations
- ✅ Checkout flow with local payment
- ✅ Payment provider variations (stripe/paypal)
- ✅ Payment failure scenarios
- ✅ Webhook endpoint accessibility
- ✅ Empty cart validation
- ✅ Order history retrieval

## Admin Interface

Access at `/admin/orders/`:
- View all orders with inline items
- View payment transactions
- Filter by status, user, date
- Readonly audit fields (created_at, updated_at)

## Future Enhancements

- [ ] Email notifications for order status changes
- [ ] Inventory management integration
- [ ] Order cancellation workflow
- [ ] Refund processing
- [ ] Multiple payment methods per order
- [ ] Installment payments
- [ ] Coupon/discount system
- [ ] Order tracking and shipping integration
