from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ProductPublicViewSet, ProductViewSet, TagViewSet

router = DefaultRouter()
router.register(r"api/products", ProductViewSet, basename="product")
router.register(r"api/categories", CategoryViewSet, basename="category")
router.register(r"api/tags", TagViewSet, basename="tag")


urlpatterns = [
    path("", include(router.urls)),
    path(
        "api/public/products",
        ProductPublicViewSet.as_view({"get": "list"}),
        name="public-products",
    ),
]
