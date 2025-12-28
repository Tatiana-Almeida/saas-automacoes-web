import time
from datetime import datetime, timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Automation, AutomationLog, AutomationRunStatus
from .services import EmailService, WhatsAppService

try:
    from croniter import croniter
except Exception:  # pragma: no cover
    croniter = None


@shared_task
def run_automation_task(automation_id: int, log_id: int = None):
    automation = Automation.objects.get(id=automation_id)
    log = None
    try:
        if log_id:
            log = AutomationLog.objects.get(id=log_id)
        else:
            log = AutomationLog.objects.create(
                automation=automation, status=AutomationRunStatus.STARTED
            )

        result = {}
        metrics = {}
        # Dry-run support
        dry_run = getattr(settings, "AUTOMATIONS_DRY_RUN", True)

        if automation.type == "whatsapp":
            if not dry_run:
                before = time.perf_counter()
                result = WhatsAppService().execute(automation.configuration)
                metrics = {
                    "attempts": result.get("attempts"),
                    "elapsed_ms": result.get("elapsed_ms"),
                    "status_code": result.get("status_code"),
                }
            else:
                result = {"message": "WhatsApp dry-run executed"}
        elif automation.type == "email":
            if not dry_run:
                before = time.perf_counter()
                result = EmailService().execute(automation.configuration)
                metrics = {
                    "elapsed_ms": int((time.perf_counter() - before) * 1000),
                    "sent": result.get("sent"),
                }
            else:
                result = {"message": "Email dry-run executed"}
        else:
            # webhook or other integrations
            result = {"message": "Generic automation executed"}

        # update log
        log.status = AutomationRunStatus.SUCCEEDED
        log.output_payload = result
        if metrics:
            log.metrics = metrics
        log.finished_at = timezone.now()
        log.save(update_fields=["status", "output_payload", "metrics", "finished_at"])

        # update automation
        automation.last_run_at = log.finished_at
        automation.last_status = AutomationRunStatus.SUCCEEDED
        automation.last_error = None
        automation.save(update_fields=["last_run_at", "last_status", "last_error"])

    except Exception as e:  # noqa
        msg = str(e)
        if log is None:
            log = AutomationLog.objects.create(
                automation=automation, status=AutomationRunStatus.FAILED
            )
        log.status = AutomationRunStatus.FAILED
        log.error_message = msg
        log.finished_at = timezone.now()
        log.save(update_fields=["status", "error_message", "finished_at"])
        automation.last_run_at = log.finished_at
        automation.last_status = AutomationRunStatus.FAILED
        automation.last_error = msg
        automation.save(update_fields=["last_run_at", "last_status", "last_error"])


@shared_task
def schedule_automations_task():
    """
    Periodic scheduler that triggers automations based on configuration.
    Supported config:
      - interval_minutes: int
    """
    now = timezone.now()
    automations = Automation.objects.filter(is_active=True)
    for a in automations:
        cfg = a.configuration or {}
        due = False

        # crontab support via 'cron': "*/5 * * * *" (if croniter available)
        cron_expr = cfg.get("cron")
        if cron_expr and croniter is not None:
            base = a.last_run_at or (now - timedelta(days=7))
            try:
                it = croniter(cron_expr, base)
                next_time = it.get_next(datetime)
                # ensure timezone-aware comparison
                if timezone.is_naive(base):
                    base = timezone.make_aware(base, timezone.get_current_timezone())
                if timezone.is_naive(now):
                    aware_now = timezone.make_aware(
                        now, timezone.get_current_timezone()
                    )
                else:
                    aware_now = now
                if isinstance(next_time, datetime) and timezone.is_naive(next_time):
                    next_time = timezone.make_aware(
                        next_time, timezone.get_current_timezone()
                    )
                due = aware_now >= next_time
            except Exception:
                # fallback to interval if cron invalid
                pass

        # interval-based scheduling
        if not due:
            interval = int(cfg.get("interval_minutes", 0) or 0)
            if interval > 0:
                if not a.last_run_at:
                    due = True
                else:
                    due = (now - a.last_run_at).total_seconds() >= interval * 60
        if not due:
            continue
        log = AutomationLog.objects.create(
            automation=a, status=AutomationRunStatus.STARTED, started_at=now
        )
        run_automation_task.delay(a.id, log.id)
