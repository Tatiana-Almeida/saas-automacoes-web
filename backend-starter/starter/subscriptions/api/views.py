from ..models import Subscription
from .serializers import SubscriptionSerializer
from starter.api.views import TenantScopedViewSet
from starter.api.permissions import IsAdminOrReadOnly


class SubscriptionViewSet(TenantScopedViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAdminOrReadOnly]
