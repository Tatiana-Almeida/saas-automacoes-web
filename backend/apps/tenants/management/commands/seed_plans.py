from apps.tenants.models import Plan
from django.core.management.base import BaseCommand

DEFAULT_PLANS = [
    {
        "code": "free",
        "name": "Free",
        "daily_limits": {
            "send_whatsapp": 100,
            "email_send": 300,
            "sms_send": 100,
            "chatbots_send": 300,
            "workflows_execute": 100,
            "ai_infer": 50,
        },
    },
    {
        "code": "pro",
        "name": "Pro",
        "daily_limits": {
            "send_whatsapp": 5000,
            "email_send": 15000,
            "sms_send": 8000,
            "chatbots_send": 20000,
            "workflows_execute": 5000,
            "ai_infer": 2000,
        },
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "daily_limits": {
            "send_whatsapp": 50000,
            "email_send": 150000,
            "sms_send": 80000,
            "chatbots_send": 200000,
            "workflows_execute": 50000,
            "ai_infer": 20000,
        },
    },
]


class Command(BaseCommand):
    help = "Seed default plans (free, pro, enterprise) with daily limits"

    def handle(self, *args, **options):
        created = 0
        for p in DEFAULT_PLANS:
            obj, was_created = Plan.objects.update_or_create(
                code=p["code"],
                defaults={
                    "name": p["name"],
                    "daily_limits": p["daily_limits"],
                },
            )
            created += int(bool(was_created))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Plan '{obj.code}' {'created' if was_created else 'updated'}"
                )
            )
        self.stdout.write(self.style.SUCCESS(f"Done. {created} created."))
