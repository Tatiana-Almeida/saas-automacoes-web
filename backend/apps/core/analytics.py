import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def track_event(event_name: str, user=None, params: dict = None):
    """Simple analytics helper.

    - If GA_MEASUREMENT_ID and GA_API_SECRET are configured, attempts to send a
      Measurement Protocol event to GA4 (best-effort).
    - Otherwise logs the event for observability.
    """
    params = params or {}
    payload = {
        "event_name": event_name,
        "user": getattr(user, "id", None) if user else None,
        "params": params,
    }

    measurement_id = getattr(settings, "GA_MEASUREMENT_ID", None)
    api_secret = getattr(settings, "GA_API_SECRET", None)

    if measurement_id and api_secret:
        try:
            import requests

            url = f"https://www.google-analytics.com/mp/collect?measurement_id={measurement_id}&api_secret={api_secret}"
            body = {
                "client_id": params.get("client_id", "server"),
                "events": [{"name": event_name, "params": params}],
            }
            resp = requests.post(url, json=body, timeout=5)
            if resp.status_code >= 400:
                logger.warning(
                    "GA track_event failed: %s %s", resp.status_code, resp.text
                )
        except Exception as e:
            logger.exception("Failed to send GA event: %s", e)
    else:
        logger.info("track_event: %s", json.dumps(payload))
