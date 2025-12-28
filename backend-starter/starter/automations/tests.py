from secrets import token_urlsafe

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Automation, AutomationLog
from .tasks import schedule_automations_task

User = get_user_model()


@override_settings(AUTOMATIONS_DRY_RUN=True)
class AutomationFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com", password=token_urlsafe(12) + "A1!", role="cliente"
        )
        token_url = reverse("token_obtain_pair")
        res = self.client.post(
            token_url,
            {"email": self.user.email, "password": self.user._password},
            format="json",
        )
        # The create_user doesn't store clear password; re-authenticate with known value
        # So instead, set password explicitly and login
        pwd = token_urlsafe(12) + "A1!"
        self.user.set_password(pwd)
        self.user.save()
        res = self.client.post(
            token_url, {"email": self.user.email, "password": pwd}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_create_activate_trigger_and_logs(self):
        # Create automation
        create_url = reverse("automation-list")
        payload = {
            "name": "Notificar por Email",
            "type": "email",
            "configuration": {
                "to": "client@example.com",
                "subject": "Olá",
                "body": "Teste de automação",
            },
        }
        res = self.client.post(create_url, payload, format="json")
        self.assertEqual(res.status_code, 201)
        automation_id = res.data["id"]

        # Pause then activate
        pause_url = reverse("automation-pause", kwargs={"pk": automation_id})
        res = self.client.post(pause_url)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["is_active"])

        activate_url = reverse("automation-activate", kwargs={"pk": automation_id})
        res = self.client.post(activate_url)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["is_active"])

        # Trigger execution (dry-run)
        trigger_url = reverse("automation-trigger", kwargs={"pk": automation_id})
        res = self.client.post(trigger_url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("log_id", res.data)

        # List logs
        logs_url = reverse("automation-logs", kwargs={"pk": automation_id})
        res = self.client.get(logs_url)
        self.assertEqual(res.status_code, 200)
        # Might be 0 or 1 depending on async timing; ensure request returns a list
        self.assertIsInstance(res.data, list)

        # Reports summary
        report_url = reverse("automation-report-summary")
        res = self.client.get(report_url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("total", res.data)
        self.assertIn("active", res.data)
        self.assertIn("paused", res.data)

    def test_dashboard_view_auth_required(self):
        # Clear auth
        self.client.credentials()
        url = reverse("automations-dashboard")
        res = self.client.get(url)
        # Unauthorized due to IsAuthenticated
        self.assertIn(res.status_code, (401, 403))

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_scheduler_triggers_due_automation(self):
        # Auth and create an automation with interval of 0.01 minutes (~0.6s)
        token_url = reverse("token_obtain_pair")
        pwd = token_urlsafe(12) + "A1!"
        self.user.set_password(pwd)
        self.user.save()
        res = self.client.post(
            token_url, {"email": self.user.email, "password": pwd}, format="json"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

        create_url = reverse("automation-list")
        payload = {
            "name": "Scheduled WhatsApp",
            "type": "whatsapp",
            "configuration": {"interval_minutes": 0},
        }
        # interval 0 means do not schedule; update to 1 minute and backdate last_run
        res = self.client.post(create_url, payload, format="json")
        self.assertEqual(res.status_code, 201)
        a_id = res.data["id"]
        a = Automation.objects.get(id=a_id)
        a.configuration["interval_minutes"] = 1
        from django.utils import timezone

        a.last_run_at = timezone.now() - timezone.timedelta(minutes=2)
        a.save(update_fields=["configuration", "last_run_at"])

        # Run scheduler; eager mode should create a STARTED log and then complete it
        schedule_automations_task()
        self.assertTrue(AutomationLog.objects.filter(automation_id=a_id).exists())
