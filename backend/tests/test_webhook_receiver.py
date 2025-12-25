import json
import hmac
import hashlib
from django.test import Client
from django.test.utils import override_settings


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_webhook_valid_signature(client: Client):
    secret = "whsec_test"
    body = json.dumps({"event": "ping"}).encode("utf-8")
    sig = _sign(secret, body)
    with override_settings(WEBHOOK_SECRETS={"custom": secret}):
        resp = client.post(
            "/api/v1/core/webhooks/custom",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE=sig,
        )
        assert resp.status_code == 200
        assert resp.json().get("data", {}).get("ok") is True


def test_webhook_missing_signature(client: Client):
    secret = "whsec_test"
    body = json.dumps({"event": "ping"}).encode("utf-8")
    with override_settings(WEBHOOK_SECRETS={"custom": secret}):
        resp = client.post(
            "/api/v1/core/webhooks/custom", data=body, content_type="application/json"
        )
        assert resp.status_code == 401


def test_webhook_invalid_signature(client: Client):
    secret = "whsec_test"
    body = json.dumps({"event": "ping"}).encode("utf-8")
    with override_settings(WEBHOOK_SECRETS={"custom": secret}):
        resp = client.post(
            "/api/v1/core/webhooks/custom",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE="bad",
        )
        assert resp.status_code == 401


def test_webhook_timestamp_skew(client: Client):
    secret = "whsec_test"
    body = json.dumps({"event": "ping"}).encode("utf-8")
    sig = _sign(secret, body)
    # Provide a timestamp far in the past to trigger skew rejection
    old_ts = 0
    with override_settings(
        WEBHOOK_SECRETS={"custom": secret}, WEBHOOK_MAX_SKEW_SECONDS=60
    ):
        resp = client.post(
            "/api/v1/core/webhooks/custom",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE=sig,
            HTTP_X_TIMESTAMP=str(old_ts),
        )
        assert resp.status_code == 400
