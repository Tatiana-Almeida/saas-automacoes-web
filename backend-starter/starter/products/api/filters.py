import django_filters

from ..models import Product


class ProductFilter(django_filters.FilterSet):
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    category = django_filters.CharFilter(
        field_name="categories__slug", lookup_expr="iexact"
    )
    tag = django_filters.CharFilter(field_name="tags__slug", lookup_expr="iexact")
    active = django_filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = Product
        fields = ["price_min", "price_max", "category", "tag", "active"]
