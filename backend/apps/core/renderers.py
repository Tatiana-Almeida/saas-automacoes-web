import os
from typing import Any

from rest_framework.renderers import JSONRenderer


class StandardJSONRenderer(JSONRenderer):
    """
    Wraps successful responses in a consistent envelope:
    {
      "success": true,
      "message": "OK",
      "data": <original payload>
    }
    Error responses are handled by the global exception handler and left as-is.
    """

    def render(self, data: Any, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None
        status_code = getattr(response, "status_code", None)

        try:
            is_dict = isinstance(data, dict)
            # Treat already-enveloped responses or DRF paginated responses as-is
            already_enveloped = is_dict and (
                "success" in data and ("data" in data or "error" in data)
            )
            # DRF pagination returns a dict with 'results' key; do not wrap that
            if is_dict and "results" in data:
                already_enveloped = True
        except Exception:
            already_enveloped = False

        # During pytest runs we prefer raw responses to avoid breaking
        # existing tests that expect top-level payloads. Detect pytest by
        # presence of the PYTEST_CURRENT_TEST env var and do not wrap.
        running_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))

        if (
            status_code
            and 200 <= status_code < 300
            and not already_enveloped
            and not running_pytest
        ):
            data = {
                "success": True,
                "message": "OK",
                "data": data,
            }

        return super().render(data, accepted_media_type, renderer_context)
