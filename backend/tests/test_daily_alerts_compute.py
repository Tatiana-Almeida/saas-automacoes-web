from apps.core.tasks import compute_daily_near_limits


def test_compute_daily_near_limits_basic():
    schema = 'testschema'
    daily_cfg = {
        'send_whatsapp': 100,
        'email_send': 50,
    }
    # Simulate cache by pre-populating keys via direct import
    from django.core.cache import cache
    from django.utils import timezone
    today = timezone.now().date().isoformat()
    cache.set(f"plan_limit:{schema}:send_whatsapp:{today}", 85, timeout=60)
    cache.set(f"plan_limit:{schema}:email_send:{today}", 10, timeout=60)

    alerts = compute_daily_near_limits(schema, daily_cfg, warn_threshold=80)
    cats = [a['category'] for a in alerts]

    assert 'send_whatsapp' in cats
    assert 'email_send' not in cats


def test_compute_daily_near_limits_threshold_change():
    schema = 'testschema2'
    daily_cfg = {
        'ai_infer': 100,
    }
    from django.core.cache import cache
    from django.utils import timezone
    today = timezone.now().date().isoformat()
    cache.set(f"plan_limit:{schema}:ai_infer:{today}", 50, timeout=60)

    # At 50% with threshold 60 -> no alert
    alerts = compute_daily_near_limits(schema, daily_cfg, warn_threshold=60)
    assert alerts == []

    # At 50% with threshold 50 -> alert
    alerts = compute_daily_near_limits(schema, daily_cfg, warn_threshold=50)
    assert len(alerts) == 1
    assert alerts[0]['category'] == 'ai_infer'
