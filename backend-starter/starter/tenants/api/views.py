from ..models import Tenant
from .serializers import TenantSerializer
from starter.api.views import TenantScopedViewSet
from starter.api.permissions import IsAdminOrReadOnly


class TenantViewSet(TenantScopedViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsAdminOrReadOnly]
