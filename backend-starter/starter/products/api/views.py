from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.db.models import Q
from ..models import Product, Category, Tag
from .serializers import (
    ProductSerializer,
    ProductWriteSerializer,
    CategorySerializer,
    TagSerializer,
)
from starter.api.views import TenantScopedViewSet
from starter.api.permissions import IsAdminOrReadOnly


class CategoryViewSet(TenantScopedViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class TagViewSet(TenantScopedViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]


class ProductViewSet(TenantScopedViewSet):
    queryset = Product.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ProductWriteSerializer
        return ProductSerializer


class ProductPublicViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        q = params.get('q')
        category = params.get('category')
        tag = params.get('tag')
        price_min = params.get('price_min')
        price_max = params.get('price_max')

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if category:
            qs = qs.filter(categories__slug=category, categories__is_active=True)
        if tag:
            qs = qs.filter(tags__slug=tag, tags__is_active=True)
        if price_min:
            qs = qs.filter(price__gte=price_min)
        if price_max:
            qs = qs.filter(price__lte=price_max)
        return qs.distinct()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'slug']
    ordering_fields = ['name', 'price', 'created_at']
