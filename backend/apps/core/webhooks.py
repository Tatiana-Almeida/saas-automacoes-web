import hashlib
import hmac
from typing import Optional, Tuple


def _strip_prefix(sig: str) -> str:
    if sig.startswith("sha256="):
        return sig.split("=", 1)[1]
    return sig


def verify_hmac_signature(secret: str, raw: bytes, signature_hex: str) -> bool:
    signature_hex = _strip_prefix(signature_hex)
    digest = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature_hex)


def parse_stripe_header(header: str) -> Tuple[Optional[int], Optional[str]]:
    """Parses Stripe-Signature header: e.g. 't=1609459200,v1=abcdef'"""
    if not header:
        return None, None
    ts = None
    v1 = None
    try:
        parts = header.split(",")
        for p in parts:
            if "=" not in p:
                continue
            k, v = p.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k == "t":
                ts = int(v)
            elif k == "v1":
                v1 = v
    except Exception:
        ts = None
        v1 = None
    return ts, v1


def verify_stripe_signature(
    secret: str, raw: bytes, header: str
) -> Tuple[bool, Optional[int]]:
    ts, v1 = parse_stripe_header(header)
    if not v1:
        return False, ts
    # Stripe signs 'timestamp.payload' with endpoint secret
    payload_to_sign = (str(ts) + ".").encode("utf-8") + raw
    digest = hmac.new(
        secret.encode("utf-8"), payload_to_sign, hashlib.sha256
    ).hexdigest()
    valid = hmac.compare_digest(digest, v1)
    return valid, ts
