from typing import Any, Dict
import logging
import traceback

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    ValidationError,
    NotAuthenticated,
    PermissionDenied,
    NotFound,
    APIException,
)


def _build_error(code: str, message: str, details: Any = None) -> Dict[str, Any]:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }


def custom_exception_handler(exc, context):
    """
    Global DRF exception handler that returns a consistent error envelope.

    Structure:
    {
      "success": false,
      "error": {
        "code": "validation_error|not_authenticated|permission_denied|not_found|error",
        "message": "human-readable message",
        "details": <original DRF error payload>
      }
    }
    """
    # Log full exception with traceback for debugging
    try:
        logging.exception(
            "Unhandled exception in DRF: %s\n%s", exc, traceback.format_exc()
        )
    except Exception:
        pass

    response: Response = drf_exception_handler(exc, context)

    if response is None:
        # Unhandled exception -> generic 500 envelope
        return Response(
            _build_error("error", "Internal server error"),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    data = response.data

    if isinstance(exc, ValidationError):
        envelope = _build_error("validation_error", "Validation error", details=data)
    elif isinstance(exc, NotAuthenticated):
        envelope = _build_error(
            "not_authenticated",
            "Authentication credentials were not provided or invalid",
            details=data,
        )
    elif isinstance(exc, PermissionDenied):
        envelope = _build_error(
            "permission_denied",
            "You do not have permission to perform this action",
            details=data,
        )
        # If the underlying exception included a `permission` detail, expose
        # it at the top-level for tests and clients that expect it.
        try:
            if isinstance(data, dict) and "permission" in data:
                perm = data.get("permission")
                # Coerce DRF ErrorDetail -> string when needed
                envelope["permission"] = str(perm)
        except Exception:
            pass
    elif isinstance(exc, NotFound):
        envelope = _build_error("not_found", "Not found", details=data)
    elif isinstance(exc, APIException):
        envelope = _build_error(
            "error", getattr(exc, "detail", "Request failed"), details=data
        )
    else:
        envelope = _build_error("error", "Request failed", details=data)

    response.data = envelope
    return response
