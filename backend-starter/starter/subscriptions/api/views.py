from starter.api.permissions import IsAdminOrReadOnly
from starter.api.views import TenantScopedViewSet

from ..models import Subscription
from .serializers import SubscriptionSerializer


class SubscriptionViewSet(TenantScopedViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAdminOrReadOnly]
