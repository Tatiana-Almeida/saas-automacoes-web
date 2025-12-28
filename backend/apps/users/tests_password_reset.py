from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class PasswordResetTests(APITestCase):
    def test_password_reset_flow(self):
        user = User.objects.create_user(
            email="pwuser@example.com", nome_completo="PW User", password="InitPass123!"
        )
        req_url = reverse("password_reset_request")
        resp = self.client.post(req_url, {"email": "pwuser@example.com"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # We can't easily capture the logged reset URL here; instead we will generate token and call confirm
        from django.contrib.auth.tokens import PasswordResetTokenGenerator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        token = PasswordResetTokenGenerator().make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        confirm_url = reverse("password_reset_confirm")
        resp = self.client.post(
            confirm_url,
            {"uid": uid, "token": token, "new_password": "NewStr0ngPass!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # login with new password
        login_url = reverse("token_obtain_pair")
        resp = self.client.post(
            login_url,
            {"email": "pwuser@example.com", "password": "NewStr0ngPass!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
