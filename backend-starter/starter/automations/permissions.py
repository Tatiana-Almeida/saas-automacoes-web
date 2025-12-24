from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user and (request.user.is_staff or getattr(request.user, 'is_superuser', False)):
            return True
        return getattr(obj, 'user_id', None) == getattr(request.user, 'id', None)
