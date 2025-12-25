from django.http import JsonResponse

from .permissions import user_has_permission


class PermissionMiddleware:
    """Middleware checks for required_permission on view functions/classes.
    Uses process_view to read attribute and enforce 403 if missing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip API routes and let DRF handle authentication + permissions
        try:
            path = getattr(request, "path", "")
            if isinstance(path, str) and path.startswith("/api/"):
                return None
        except Exception:
            pass
        required = getattr(view_func, "required_permission", None)
        # Class-based views store attribute on the 'view_class' as well
        if not required and hasattr(view_func, "view_class"):
            required = getattr(view_func.view_class, "required_permission", None)
        if not required:
            return None
        tenant = getattr(request, "tenant", None)
        if user_has_permission(getattr(request, "user", None), required, tenant):
            return None
        return JsonResponse(
            {"detail": "Permissão negada", "permission": required}, status=403
        )
