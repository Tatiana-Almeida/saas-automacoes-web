from starter.api.permissions import IsAdminOrReadOnly
from starter.api.views import TenantScopedViewSet

from ..models import Tenant
from .serializers import TenantSerializer


class TenantViewSet(TenantScopedViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsAdminOrReadOnly]
