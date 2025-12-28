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


class WhatsAppService:
    def execute(self, config: dict) -> dict:
        """
        Expected config keys:
          - api_url: str
          - token: str
          - to: str
          - message: str
        """
        api_url = config.get("api_url")
        token = config.get("token")
        to = config.get("to")
        message = config.get("message")
        if not api_url or not token or not to or not message:
            raise ValueError("Invalid WhatsApp configuration")
        max_attempts = int(config.get("max_attempts", 3))
        backoff_base = float(config.get("backoff_base", 0.5))  # seconds
        attempt = 0
        last_exc = None
        start = time.perf_counter()

        if not requests:
            logger.warning("requests not available, simulating WhatsApp call")
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            return {
                "simulated": True,
                "to": to,
                "message": message,
                "attempts": 1,
                "elapsed_ms": elapsed_ms,
            }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = json.dumps({"to": to, "message": message})
        status_code = None

        while attempt < max_attempts:
            attempt += 1
            try:
                req_start = time.perf_counter()
                resp = requests.post(api_url, headers=headers, data=payload, timeout=15)
                status_code = resp.status_code
                resp.raise_for_status()
                total_ms = int((time.perf_counter() - start) * 1000)
                per_attempt_ms = int((time.perf_counter() - req_start) * 1000)
                data = resp.json() if resp.content else {}
                data.update(
                    {
                        "status_code": status_code,
                        "attempts": attempt,
                        "elapsed_ms": total_ms,
                        "last_attempt_ms": per_attempt_ms,
                    }
                )
                return data
            except Exception as e:  # noqa
                last_exc = e
                if attempt >= max_attempts:
                    break
                sleep_for = backoff_base * (2 ** (attempt - 1))
                time.sleep(sleep_for)
        # If we exit loop, raise the last exception with metrics context
        total_ms = int((time.perf_counter() - start) * 1000)
        msg = f"WhatsApp send failed after {attempt} attempts (status={status_code})"
        logger.error(msg)
        raise RuntimeError(msg) from last_exc


class EmailService:
    def execute(self, config: dict) -> dict:
        """
        Expected config keys:
          - to: str | list[str]
          - subject: str
          - body: str
        """
        to = config.get("to")
        subject = config.get("subject", "Automation Notification")
        body = config.get("body", "")
        if not to:
            raise ValueError('Email config must include "to"')
        if isinstance(to, str):
            to_list = [to]
        else:
            to_list = list(to)
        max_attempts = int(config.get("max_attempts", 3))
        backoff_base = float(config.get("backoff_base", 0.5))
        attempt = 0
        last_exc = None
        start = time.perf_counter()

        while attempt < max_attempts:
            attempt += 1
            try:
                req_start = time.perf_counter()
                sent = send_mail(
                    subject,
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    to_list,
                    fail_silently=False,
                )
                total_ms = int((time.perf_counter() - start) * 1000)
                per_attempt_ms = int((time.perf_counter() - req_start) * 1000)
                return {
                    "sent": sent,
                    "to": to_list,
                    "attempts": attempt,
                    "elapsed_ms": total_ms,
                    "last_attempt_ms": per_attempt_ms,
                }
            except Exception as e:  # pragma: no cover
                last_exc = e
                if attempt >= max_attempts:
                    break
                time.sleep(backoff_base * (2 ** (attempt - 1)))
        # if we reach here, all attempts failed
        msg = f"Email send failed after {attempt} attempts"
        logger.error(msg)
        raise RuntimeError(msg) from last_exc
