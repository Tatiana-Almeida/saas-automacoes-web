from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthTests(APITestCase):
    def test_register_and_login(self):
        url = reverse('auth_register')
        data = {'email': 'testuser@example.com', 'nome_completo': 'Test User', 'password': 'Str0ngPass!'}
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='testuser@example.com').exists())

        # Login with email (SimpleJWT uses USERNAME_FIELD which is 'email')
        login_url = reverse('token_obtain_pair')
        resp = self.client.post(login_url, {'email': 'testuser@example.com', 'password': 'Str0ngPass!'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
