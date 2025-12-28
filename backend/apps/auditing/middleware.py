from .models import AuditLog
from .utils import get_client_ip


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            user = getattr(request, "user", None)
            tenant = getattr(request, "tenant", None)
            schema = getattr(tenant, "schema_name", None)
            tenant_id = getattr(tenant, "id", None)
            ip = get_client_ip(request)

            # Determine action type heuristically
            path = request.path or ""
            action = "request"
            if path.endswith("/auth/token") and request.method == "POST":
                action = "login"
            elif path.endswith("/auth/logout") and request.method == "POST":
                action = "logout"
            elif getattr(response, "status_code", 200) >= 400:
                action = "error"

            AuditLog.objects.create(
                user=(
                    user
                    if (user and getattr(user, "is_authenticated", False))
                    else None
                ),
                path=path,
                method=request.method,
                source="middleware",
                action=action,
                status_code=getattr(response, "status_code", None),
                tenant_schema=schema,
                tenant_id=tenant_id,
                ip_address=ip,
            )
        except Exception:
            # Never block the request due to auditing failures
            pass

        return response
