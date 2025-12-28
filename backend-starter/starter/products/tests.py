from secrets import token_urlsafe

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from starter.products.models import Category, Product, Tag

User = get_user_model()


class ProductModuleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self._pwd_admin = token_urlsafe(12) + "A1!"
        self._pwd_client = token_urlsafe(12) + "A1!"
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password=self._pwd_admin,
            role="admin",
            is_staff=True,
        )
        self.client_user = User.objects.create_user(
            email="client@example.com", password=self._pwd_client, role="cliente"
        )
        self.category = Category.objects.create(name="Chatbots")
        self.tag = Tag.objects.create(name="AI")

    def test_public_list_shows_only_active(self):
        Product.objects.create(
            name="Auto001", description="Desc", price="99.90", is_active=True
        )
        Product.objects.create(
            name="Auto002", description="Desc", price="149.90", is_active=False
        )
        url = reverse("public-products")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = (
            res.data["results"]
            if isinstance(res.data, dict) and "results" in res.data
            else res.data
        )
        names = [item["name"] for item in data]
        self.assertIn("Auto001", names)
        self.assertNotIn("Auto002", names)

    def test_public_filters_by_category_tag_price_and_search(self):
        p1 = Product.objects.create(
            name="AutoChat", description="Ferramenta AI", price="99.90", is_active=True
        )
        p1.categories.add(self.category)
        p1.tags.add(self.tag)
        Product.objects.create(
            name="Webhooker", description="Integrações", price="199.90", is_active=True
        )
        # filter by category slug
        url = reverse("public-products")
        res_cat = self.client.get(url, {"category": self.category.slug})
        self.assertEqual(res_cat.status_code, 200)
        data_cat = (
            res_cat.data["results"]
            if isinstance(res_cat.data, dict) and "results" in res_cat.data
            else res_cat.data
        )
        self.assertTrue(any(item["name"] == "AutoChat" for item in data_cat))
        # filter by tag slug
        res_tag = self.client.get(url, {"tag": self.tag.slug})
        data_tag = (
            res_tag.data["results"]
            if isinstance(res_tag.data, dict) and "results" in res_tag.data
            else res_tag.data
        )
        self.assertTrue(any(item["name"] == "AutoChat" for item in data_tag))
        # price range
        res_price = self.client.get(url, {"price_min": "150", "price_max": "250"})
        data_price = (
            res_price.data["results"]
            if isinstance(res_price.data, dict) and "results" in res_price.data
            else res_price.data
        )
        self.assertTrue(any(item["name"] == "Webhooker" for item in data_price))
        # search
        res_search = self.client.get(url, {"q": "chat"})
        data_search = (
            res_search.data["results"]
            if isinstance(res_search.data, dict) and "results" in res_search.data
            else res_search.data
        )
        self.assertTrue(any("AutoChat" == item["name"] for item in data_search))

    def test_public_filter_active_param(self):
        Product.objects.create(
            name="ActiveOne", description="Desc", price="10.00", is_active=True
        )
        Product.objects.create(
            name="InactiveOne", description="Desc", price="20.00", is_active=False
        )
        url = reverse("public-products")
        # default: only active
        res_default = self.client.get(url)
        data_default = (
            res_default.data["results"]
            if isinstance(res_default.data, dict) and "results" in res_default.data
            else res_default.data
        )
        names_default = [item["name"] for item in data_default]
        self.assertIn("ActiveOne", names_default)
        self.assertNotIn("InactiveOne", names_default)
        # explicit active=false still yields none (public endpoint constrained)
        res_inactive = self.client.get(url, {"active": "false"})
        data_inactive = (
            res_inactive.data["results"]
            if isinstance(res_inactive.data, dict) and "results" in res_inactive.data
            else res_inactive.data
        )
        names_inactive = [item["name"] for item in data_inactive]
        self.assertNotIn("InactiveOne", names_inactive)

    def test_admin_can_create_product_with_category(self):
        url = reverse("product-list")
        data = {
            "name": "Auto003",
            "description": "Desc detalhada",
            "price": "199.99",
            "is_active": True,
            "category_ids": [self.category.id],
        }
        # auth as admin
        token_url = reverse("token_obtain_pair")
        res = self.client.post(
            token_url,
            {"email": self.admin.email, "password": self._pwd_admin},
            format="json",
        )
        access = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        res_create = self.client.post(url, data, format="multipart")
        self.assertEqual(res_create.status_code, 201)
        self.assertTrue(Product.objects.filter(name="Auto003").exists())

    def test_client_cannot_create_product(self):
        url = reverse("product-list")
        data = {
            "name": "Auto004",
            "description": "Desc",
            "price": "49.99",
            "is_active": True,
        }
        # auth as client
        token_url = reverse("token_obtain_pair")
        res = self.client.post(
            token_url,
            {"email": self.client_user.email, "password": self._pwd_client},
            format="json",
        )
        access = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        res_create = self.client.post(url, data, format="json")
        self.assertEqual(res_create.status_code, 403)
