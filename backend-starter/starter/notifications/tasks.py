from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Notification, NotificationLog, NotificationStatus
from .services import NotificationService

User = get_user_model()


@shared_task
def send_notification_task(notification_id: int):
    notif = Notification.objects.get(id=notification_id)
    svc = NotificationService()
    attempt = notif.attempts + 1
    output = {}
    try:
        if notif.channel == "email":
            output = svc.send_email(notif.to, notif.title, notif.body, notif.payload)
        elif notif.channel == "sms":
            cfg = notif.payload or {}
            output = svc.send_sms(
                cfg.get("api_url", ""), cfg.get("token", ""), notif.to, notif.body
            )
        elif notif.channel == "whatsapp":
            cfg = notif.payload or {}
            output = svc.send_whatsapp(
                cfg.get("api_url", ""), cfg.get("token", ""), notif.to, notif.body
            )
        # success
        notif.status = NotificationStatus.SENT
        notif.attempts = attempt
        notif.sent_at = timezone.now()
        notif.last_error = None
        notif.save(update_fields=["status", "attempts", "sent_at", "last_error"])
        NotificationLog.objects.create(
            notification=notif,
            status=NotificationStatus.SENT,
            attempt=attempt,
            response_payload=output,
            metrics={
                k: output.get(k)
                for k in ("elapsed_ms", "attempts", "last_attempt_ms", "status_code")
                if k in output
            },
        )
    except Exception as e:  # noqa
        notif.status = NotificationStatus.FAILED
        notif.attempts = attempt
        notif.last_error = str(e)
        notif.save(update_fields=["status", "attempts", "last_error"])
        NotificationLog.objects.create(
            notification=notif,
            status=NotificationStatus.FAILED,
            attempt=attempt,
            message=str(e),
        )


@shared_task
def send_event_notification_task(
    event: str,
    user_id: int,
    title: str,
    body: str,
    channel: str = "email",
    payload: dict | None = None,
):
    user = User.objects.get(id=user_id)
    to = user.email if channel == "email" else payload.get("to") if payload else ""
    notif = Notification.objects.create(
        user=user,
        channel=channel,
        to=to or "",
        title=title,
        body=body,
        payload=payload or {},
    )
    send_notification_task.delay(notif.id)
    return notif.id


@shared_task
def generate_reports_task(start_iso: str | None = None, end_iso: str | None = None):
    # Stub heavy report job (could persist results if desired)
    from django.utils.dateparse import parse_datetime
    from starter.automations.models import AutomationLog, AutomationRunStatus
    from starter.orders.models import Order, OrderStatus
    from starter.users.models import User as AppUser

    start = parse_datetime(start_iso) if start_iso else None
    end = parse_datetime(end_iso) if end_iso else None
    qs_orders = Order.objects.filter(status=OrderStatus.PAID)
    if start:
        qs_orders = qs_orders.filter(ordered_at__gte=start)
    if end:
        qs_orders = qs_orders.filter(ordered_at__lte=end)
    revenue = sum((o.total for o in qs_orders), start=0)

    logs = AutomationLog.objects.all()
    if start:
        logs = logs.filter(created_at__gte=start)
    if end:
        logs = logs.filter(created_at__lte=end)
    succeeded = logs.filter(status=AutomationRunStatus.SUCCEEDED).count()
    failed = logs.filter(status=AutomationRunStatus.FAILED).count()

    active_users = AppUser.objects.filter(is_active=True).count()

    return {
        "revenue": str(revenue),
        "paid_orders": qs_orders.count(),
        "automations_succeeded": succeeded,
        "automations_failed": failed,
        "active_users": active_users,
    }
