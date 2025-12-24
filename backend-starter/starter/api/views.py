from rest_framework import viewsets, permissions


class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class TenantScopedViewSet(BaseViewSet):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs
