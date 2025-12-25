import json
from django.test import Client
from django.test.utils import override_settings

from apps.core.webhooks import verify_stripe_signature


def _stripe_header(secret: str, body: bytes, ts: int) -> str:
    import hmac, hashlib

    payload = (str(ts) + ".").encode("utf-8") + body
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def test_stripe_signature_valid(client: Client):
    secret = "whsec_stripe"
    ts = 1700000000  # arbitrary timestamp
    body = json.dumps({"type": "ping"}).encode("utf-8")
    header = _stripe_header(secret, body, ts)
    with override_settings(
        WEBHOOK_SECRETS={"stripe": secret}, WEBHOOK_MAX_SKEW_SECONDS=10**9
    ):
        resp = client.post(
            "/api/v1/core/webhooks/stripe",
            data=body,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=header,
        )
        assert resp.status_code == 200
        assert resp.json().get("data", {}).get("ok") is True


def test_stripe_signature_missing_header(client: Client):
    secret = "whsec_stripe"
    body = json.dumps({"type": "ping"}).encode("utf-8")
    with override_settings(WEBHOOK_SECRETS={"stripe": secret}):
        resp = client.post(
            "/api/v1/core/webhooks/stripe",
            data=body,
            content_type="application/json",
        )
        assert resp.status_code == 401
        assert "Missing" in resp.json().get("detail", "")
