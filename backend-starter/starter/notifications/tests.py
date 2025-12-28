from secrets import token_urlsafe

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from starter.notifications.models import Notification

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class NotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # admin
        self.admin_pwd = token_urlsafe(12) + "A1!"
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password=self.admin_pwd,
            role="admin",
            is_staff=True,
        )
        # client
        self.user_pwd = token_urlsafe(12) + "A1!"
        self.user = User.objects.create_user(
            email="user@example.com", password=self.user_pwd, role="cliente"
        )
        # auth admin
        token_url = reverse("token_obtain_pair")
        res = self.client.post(
            token_url,
            {"email": self.admin.email, "password": self.admin_pwd},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_manual_send_email_notification(self):
        url = reverse("notification-send-manual")
        payload = {
            "user_id": self.user.id,
            "channel": "email",
            "to": self.user.email,
            "title": "Boas-vindas",
            "body": "Olá!",
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, 201)
        notif_id = res.data["id"]
        # History for this user (as admin)
        hist_url = reverse("notifications-history")
        res_hist = self.client.get(hist_url, {"user_id": self.user.id})
        self.assertEqual(res_hist.status_code, 200)
        self.assertTrue(any(n["id"] == notif_id for n in res_hist.data))

    def test_reports_summary_endpoint(self):
        url = reverse("reports-summary")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("revenue", res.data)
        self.assertIn("automations", res.data)
        self.assertIn("notifications", res.data)

    def test_events_enqueue_endpoint(self):
        url = reverse("notifications-events")
        payload = {
            "event": "payment_succeeded",
            "user_id": self.user.id,
            "title": "Pagamento aprovado",
            "body": "Obrigado!",
        }
        res = self.client.post(url, payload, format="json")
        self.assertIn(res.status_code, (202, 200))

    def test_user_history_mine_filter(self):
        # auth as user
        token_url = reverse("token_obtain_pair")
        res = self.client.post(
            token_url,
            {"email": self.user.email, "password": self.user_pwd},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        # Create a notification for user
        n = Notification.objects.create(
            user=self.user,
            channel="email",
            to=self.user.email,
            title="Teste",
            body="Body",
        )
        url = reverse("notifications-history")
        res = self.client.get(url, {"mine": "true"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(any(item["id"] == n.id for item in res.data))
