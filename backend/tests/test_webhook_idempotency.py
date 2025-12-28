import json

from django.test import Client
from django.test.utils import override_settings


def _stripe_header(secret: str, body: bytes, ts: int) -> str:
    import hashlib
    import hmac

    payload = (str(ts) + ".").encode("utf-8") + body
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def test_stripe_idempotency(client: Client):
    secret = "whsec_stripe"
    ts = 1700000000
    # Include a deterministic event id
    evt = {"id": "evt_test_123", "type": "invoice.payment_succeeded"}
    body = json.dumps(evt).encode("utf-8")
    header = _stripe_header(secret, body, ts)
    with override_settings(
        WEBHOOK_SECRETS={"stripe": secret},
        WEBHOOK_MAX_SKEW_SECONDS=10**9,
        WEBHOOK_IDEMPOTENCY_TTL_SECONDS=60,
    ):
        # First call: should be processed (idempotent=False)
        resp1 = client.post(
            "/api/v1/core/webhooks/stripe",
            data=body,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header,
        )
        assert resp1.status_code == 200
        assert resp1.json().get("data", {}).get("ok") is True
        assert resp1.json().get("data", {}).get("idempotent") is False
        # Second call with same event id: should be idempotent=True
        resp2 = client.post(
            "/api/v1/core/webhooks/stripe",
            data=body,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header,
        )
        assert resp2.status_code == 200
        assert resp2.json().get("data", {}).get("ok") is True
        assert resp2.json().get("data", {}).get("idempotent") is True
