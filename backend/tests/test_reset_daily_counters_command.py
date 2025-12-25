import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from apps.tenants.models import Tenant


@pytest.mark.django_db
def test_reset_daily_counters_command_with_categories(create_tenant):
    t = create_tenant(
        schema_name="acme", domain="acme.localhost", name="ACME", plan="free"
    )
    today = timezone.now().date().isoformat()

    key1 = f"plan_limit:{t.schema_name}:send_whatsapp:{today}"
    key2 = f"plan_limit:{t.schema_name}:send_email:{today}"
    cache.set(key1, 4, timeout=60)
    cache.set(key2, 2, timeout=60)

    call_command(
        "reset_daily_counters",
        "--schema",
        "acme",
        "--categories",
        "send_whatsapp",
        "send_email",
    )

    assert int(cache.get(key1, 0)) == 0
    assert int(cache.get(key2, 0)) == 0


@pytest.mark.django_db
@override_settings(
    TENANT_PLAN_DAILY_LIMITS={
        "free": {
            "send_sms": 3,
        }
    }
)
def test_reset_daily_counters_command_all_categories_from_plan(create_tenant):
    t = create_tenant(
        schema_name="beta", domain="beta.localhost", name="Beta", plan="free"
    )
    today = timezone.now().date().isoformat()

    key = f"plan_limit:{t.schema_name}:send_sms:{today}"
    cache.set(key, 5, timeout=60)

    call_command("reset_daily_counters", "--schema", "beta")

    assert int(cache.get(key, 0)) == 0
