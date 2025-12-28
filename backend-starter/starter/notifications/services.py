import json
import logging
import time

from django.conf import settings
from django.core.mail import send_mail

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

logger = logging.getLogger(__name__)


class NotificationService:
    def send_email(
        self,
        to: str,
        title: str,
        body: str,
        payload: dict | None = None,
        *,
        max_attempts: int = 3,
        backoff_base: float = 0.5,
    ) -> dict:
        attempt = 0
        last_exc = None
        start = time.perf_counter()
        while attempt < max_attempts:
            attempt += 1
            try:
                t0 = time.perf_counter()
                sent = send_mail(
                    title, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False
                )
                total_ms = int((time.perf_counter() - start) * 1000)
                per_attempt_ms = int((time.perf_counter() - t0) * 1000)
                return {
                    "sent": sent,
                    "attempts": attempt,
                    "elapsed_ms": total_ms,
                    "last_attempt_ms": per_attempt_ms,
                }
            except Exception as e:  # pragma: no cover
                last_exc = e
                if attempt >= max_attempts:
                    break
                time.sleep(backoff_base * (2 ** (attempt - 1)))
        msg = f"Email delivery failed after {attempt} attempts"
        logger.error(msg)
        raise RuntimeError(msg) from last_exc

    def send_sms(
        self,
        api_url: str,
        token: str,
        to: str,
        body: str,
        *,
        max_attempts: int = 3,
        backoff_base: float = 0.5,
    ) -> dict:
        start = time.perf_counter()
        if not requests:
            logger.warning("requests not available, simulating SMS call")
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return {
                "simulated": True,
                "to": to,
                "elapsed_ms": elapsed_ms,
                "attempts": 1,
            }
        attempt = 0
        last_exc = None
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        data = json.dumps({"to": to, "message": body})
        while attempt < max_attempts:
            attempt += 1
            try:
                t0 = time.perf_counter()
                resp = requests.post(api_url, headers=headers, data=data, timeout=15)
                resp.raise_for_status()
                total_ms = int((time.perf_counter() - start) * 1000)
                last_ms = int((time.perf_counter() - t0) * 1000)
                out = resp.json() if resp.content else {}
                out.update(
                    {
                        "status_code": resp.status_code,
                        "attempts": attempt,
                        "elapsed_ms": total_ms,
                        "last_attempt_ms": last_ms,
                    }
                )
                return out
            except Exception as e:
                last_exc = e
                if attempt >= max_attempts:
                    break
                time.sleep(backoff_base * (2 ** (attempt - 1)))
        msg = f"SMS delivery failed after {attempt} attempts"
        logger.error(msg)
        raise RuntimeError(msg) from last_exc

    def send_whatsapp(
        self,
        api_url: str,
        token: str,
        to: str,
        body: str,
        *,
        max_attempts: int = 3,
        backoff_base: float = 0.5,
    ) -> dict:
        # Same pattern as SMS
        return self.send_sms(
            api_url,
            token,
            to,
            body,
            max_attempts=max_attempts,
            backoff_base=backoff_base,
        )
