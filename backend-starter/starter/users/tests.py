from django.urls import reverse
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from secrets import token_urlsafe

User = get_user_model()

class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = token_urlsafe(12)+'A1!'
        self.user = User.objects.create_user(email='admin@example.com', password=self.password, role='admin')

    def test_register(self):
        new_pwd = token_urlsafe(12)+'A1!'
        payload = {'email': 'new@example.com','password': new_pwd}
        url = reverse('auth-register')
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

    def test_register_duplicate_email(self):
        payload = {'email': self.user.email,'password': token_urlsafe(12)+'A1!'}
        url = reverse('auth-register')
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('email', res.data)

    def test_register_weak_password(self):
        payload = {'email': 'weak@example.com','password': '1'*8}
        url = reverse('auth-register')
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('password', res.data)

    def test_token_obtain_and_me(self):
        # Obtain token
        url = reverse('token_obtain_pair')
        res = self.client.post(url, {'email': self.user.email, 'password': self.password}, format='json')
        self.assertEqual(res.status_code, 200)
        access = res.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        # Me endpoint
        me_url = reverse('users-me')
        res_me = self.client.get(me_url)
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(res_me.data['email'], self.user.email)

    def test_password_reset_request(self):
        url = reverse('auth-password-reset')
        res = self.client.post(url, {'email': self.user.email}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data.get('sent'))

    def test_logout_blacklists_refresh(self):
        # Obtain tokens
        obtain_url = reverse('token_obtain_pair')
        res = self.client.post(obtain_url, {'email': self.user.email, 'password': self.password}, format='json')
        self.assertEqual(res.status_code, 200)
        refresh = res.data['refresh']
        access = res.data['access']
        # Logout (blacklist refresh)
        logout_url = reverse('auth-logout')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        res_logout = self.client.post(logout_url, {'refresh': refresh}, format='json')
        self.assertIn(res_logout.status_code, (200, 205))
        # Try to refresh with blacklisted token
        refresh_url = reverse('token_refresh')
        res_refresh = self.client.post(refresh_url, {'refresh': refresh}, format='json')
        self.assertNotEqual(res_refresh.status_code, 200)

    def test_password_reset_confirm(self):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import PasswordResetTokenGenerator
        generator = PasswordResetTokenGenerator()
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = generator.make_token(self.user)
        new_pwd = token_urlsafe(12)+'A1!'
        url = reverse('auth-password-reset-confirm')
        res = self.client.post(url, {'uid': uid, 'token': token, 'new_password': new_pwd}, format='json')
        self.assertEqual(res.status_code, 200)
        # login with new password
        obtain_url = reverse('token_obtain_pair')
        res_login = self.client.post(obtain_url, {'email': self.user.email, 'password': new_pwd}, format='json')
        self.assertEqual(res_login.status_code, 200)

    def test_password_reset_confirm_invalid_token(self):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        bad_token = 'invalid-token'
        url = reverse('auth-password-reset-confirm')
        res = self.client.post(url, {'uid': uid, 'token': bad_token, 'new_password': token_urlsafe(12)+'A1!'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('token', res.data)

    def test_password_reset_confirm_invalid_uid(self):
        token = 'some-token'
        url = reverse('auth-password-reset-confirm')
        res = self.client.post(url, {'uid': 'bad-uid', 'token': token, 'new_password': token_urlsafe(12)+'A1!'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('uid', res.data)
