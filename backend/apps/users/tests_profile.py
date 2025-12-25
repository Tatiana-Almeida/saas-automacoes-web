from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileEditTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="me@example.com", nome_completo="Me", password="InitPass1!"
        )
        self.other = User.objects.create_user(
            email="other@example.com", nome_completo="Other", password="InitPass1!"
        )
        login_url = reverse("token_obtain_pair")
        resp = self.client.post(
            login_url,
            {"email": "me@example.com", "password": "InitPass1!"},
            format="json",
        )
        token = resp.data.get("access")
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_edit_own_profile(self):
        url = reverse("users_me")
        resp = self.client.patch(
            url,
            {"nome_completo": "New Name", "telefone": "12345"},
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.nome_completo, "New Name")
        self.assertEqual(self.user.telefone, "12345")

    def test_cannot_edit_other_user_via_me(self):
        # /users/me only edits the authenticated user; attempt to edit other user via direct model (should not be possible via endpoint)
        url = reverse("users_me")
        # try to set email to other's email
        resp = self.client.patch(
            url, {"email": "other@example.com"}, format="json", **self.auth_headers
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
