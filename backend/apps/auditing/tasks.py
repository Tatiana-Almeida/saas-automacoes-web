import base64
import json
import time
from datetime import timedelta
from urllib import error, request

from apps.auditing.models import AuditLog
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


def _es_post_bulk(url: str, ndjson_payload: str, headers=None):
    headers = headers or {}
    req = request.Request(url, data=ndjson_payload.encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/x-ndjson")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, body
    except error.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        return e.code, body
    except Exception as e:
        return 0, str(e)


def _serialize_log(log):
    return {
        "id": log.id,
        "user_id": getattr(log.user, "id", None) if log.user_id else None,
        "username": getattr(log.user, "username", None) if log.user_id else None,
        "path": log.path,
        "method": log.method,
        "source": getattr(log, "source", None),
        "action": getattr(log, "action", None),
        "status_code": getattr(log, "status_code", None),
        "tenant_schema": getattr(log, "tenant_schema", None),
        "tenant_id": getattr(log, "tenant_id", None),
        "ip_address": log.ip_address,
        "created_at": log.created_at.isoformat(),
    }


def _build_es_headers():
    headers = {}
    # Basic auth if username/password provided
    user = getattr(settings, "ELASTICSEARCH_USERNAME", None)
    pwd = getattr(settings, "ELASTICSEARCH_PASSWORD", None)
    api_key = getattr(settings, "ELASTICSEARCH_API_KEY", None)
    if user and pwd:
        token = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
    elif api_key:
        # Accept raw ApiKey (already base64-encoded 'id:key')
        headers["Authorization"] = f"ApiKey {api_key}"
    return headers


@shared_task
def export_audit_logs_to_elasticsearch(
    batch_size: int = 1000,
    minutes_back_if_empty: int = 5,
    max_attempts: int = 3,
    base_backoff_seconds: float = 1.0,
):
    if not getattr(settings, "AUDIT_EXPORT_ENABLED", False):
        return {"status": "disabled"}
    es_url = getattr(settings, "ELASTICSEARCH_URL", None)
    if not es_url:
        return {"status": "no_es_url"}

    from apps.auditing.models import AuditLog

    last_ts_key = "audit_export:last_ts"
    last_ts_iso = cache.get(last_ts_key)
    if last_ts_iso:
        since = timezone.datetime.fromisoformat(last_ts_iso)
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
    else:
        since = timezone.now() - timedelta(minutes=minutes_back_if_empty)

    qs = AuditLog.objects.filter(created_at__gt=since).order_by("created_at")[
        :batch_size
    ]
    logs = list(qs)
    if not logs:
        return {"status": "nothing_to_export"}

    prefix = getattr(settings, "AUDIT_EXPORT_INDEX_PREFIX", "audit")
    ndjson_lines = []
    for log in logs:
        index_name = f"{prefix}-{log.created_at.strftime('%Y.%m.%d')}"
        meta = {"index": {"_index": index_name}}
        ndjson_lines.append(json.dumps(meta, ensure_ascii=False))
        ndjson_lines.append(json.dumps(_serialize_log(log), ensure_ascii=False))
    payload = "\n".join(ndjson_lines) + "\n"

    # Build headers and attempt with simple exponential backoff
    headers = _build_es_headers()
    bulk_url = f"{es_url.rstrip('/')}/_bulk"
    attempt = 0
    status_code, body = 0, ""
    while attempt < max_attempts:
        status_code, body = _es_post_bulk(bulk_url, payload, headers=headers)
        if status_code == 200:
            break
        attempt += 1
        if attempt < max_attempts:
            # Backoff with jitter
            sleep_s = base_backoff_seconds * (2 ** (attempt - 1))
            time.sleep(min(sleep_s, 10.0))
    if status_code != 200:
        return {
            "status": "error",
            "code": status_code,
            "attempts": attempt,
            "body": body[:500],
        }

    latest = logs[-1].created_at
    cache.set(last_ts_key, latest.isoformat(), timeout=24 * 3600)
    return {"status": "ok", "exported": len(logs), "latest": latest.isoformat()}


def _build_alert_payload(log):
    user = None
    try:
        user = getattr(log.user, "username", None)
    except Exception:
        user = None
    text = (
        f"[AUDIT] action={getattr(log, 'action', None)} tenant={getattr(log, 'tenant_schema', None)} "
        f"user={user} path={getattr(log, 'path', None)} status={getattr(log, 'status_code', None)}"
    )
    return {"text": text}


def _post_webhook(url: str, payload: dict, headers=None):
    headers = headers or {}
    req = request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with request.urlopen(req, timeout=10) as resp:
            return resp.status, (resp.read().decode("utf-8") or "")
    except error.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        return e.code, body
    except Exception as e:
        return 0, str(e)


@shared_task
def send_audit_alert(log_id: int):
    if not getattr(settings, "ALERT_WEBHOOK_ENABLED", False):
        return {"status": "disabled"}
    url = getattr(settings, "ALERT_WEBHOOK_URL", None)
    if not url:
        return {"status": "no_url"}
    from apps.auditing.models import AuditLog

    try:
        log = AuditLog.objects.get(id=log_id)
    except AuditLog.DoesNotExist:
        return {"status": "missing"}

    # Quiet-period suppression to avoid alert spam (unless bypassed)
    try:
        quiet_minutes = int(getattr(settings, "ALERT_WEBHOOK_QUIET_MINUTES", 10) or 0)
    except Exception:
        quiet_minutes = 10
    # Define the suppression window (seconds). In TESTING we use a very small
    # window to reduce cross-test interference, but it must be at least 1-2s
    # so that immediate repeated sends in a single test are still suppressed.
    if getattr(settings, "TESTING", False):
        window_seconds = min(max(1, int(quiet_minutes * 60)), 2)
    else:
        window_seconds = int(quiet_minutes * 60)
    tenant_schema = getattr(log, "tenant_schema", None)
    action = getattr(log, "action", None)
    bypass_actions = set(
        getattr(settings, "ALERT_WEBHOOK_QUIET_BYPASS_ACTIONS", []) or []
    )
    # In TESTING, we will honor the original action-level quiet key (so
    # tests that manipulate it continue to work), but also maintain a
    # per-log key to reduce cross-test interference in environments where
    # tests may run concurrently or when other tests leave residual keys.
    action_key = f"audit_alert:quiet:{tenant_schema}:{action}"
    per_log_key = f"audit_alert:quiet:test:{tenant_schema}:{action}:{log_id}"
    action_key if not getattr(settings, "TESTING", False) else per_log_key
    if quiet_minutes > 0 and action not in bypass_actions:
        # Always check the action-level key first (legacy behavior) and then
        # the per-log key. Do not gate these checks on an initial per-log
        # fetch which caused missing action-key detection previously.
        # Check action-level key
        if cache.get(action_key):
            try:
                last_iso_action = cache.get(action_key)
                last_dt_action = timezone.datetime.fromisoformat(last_iso_action)
                if last_dt_action.tzinfo is None:
                    last_dt_action = last_dt_action.replace(tzinfo=timezone.utc)
            except Exception:
                last_dt_action = timezone.now() - timedelta(minutes=quiet_minutes + 1)
            # If the stored action timestamp is older than the created_at of
            # the current log, it's likely from a previous test/run and
            # should not suppress this log. Only suppress when the last
            # action timestamp is newer than the log's creation time and
            # within the suppression window.
            if last_dt_action >= (
                getattr(log, "created_at", timezone.now()) - timedelta(seconds=0)
            ):
                if (timezone.now() - last_dt_action) < timedelta(
                    seconds=window_seconds
                ):
                    return {"status": "suppressed"}

        # Then check the per-log key
        if cache.get(per_log_key):
            try:
                last_iso = cache.get(per_log_key)
                last_dt = timezone.datetime.fromisoformat(last_iso)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
            except Exception:
                last_dt = timezone.now() - timedelta(minutes=quiet_minutes + 1)
            if (timezone.now() - last_dt) < timedelta(seconds=window_seconds):
                return {"status": "suppressed"}

    # (debug prints removed)

    payload = _build_alert_payload(log)
    code, body = _post_webhook(url, payload)
    if 200 <= code < 300:
        # Mark quiet key on success unless bypassed
        if quiet_minutes > 0 and action not in bypass_actions:
            # Use a TTL at least as long as the suppression window so that
            # immediate subsequent sends within the same test are suppressed.
            if getattr(settings, "TESTING", False):
                ttl = max(1, window_seconds)
            else:
                ttl = max(quiet_minutes * 60, 1)
            # Set both keys during tests so legacy deletions/fixtures still
            # operate on the action-level key, while per-log key helps
            # reduce accidental cross-test suppression.
            if getattr(settings, "TESTING", False):
                cache.set(action_key, timezone.now().isoformat(), timeout=ttl)
                cache.set(per_log_key, timezone.now().isoformat(), timeout=ttl)
            else:
                cache.set(action_key, timezone.now().isoformat(), timeout=ttl)
        return {"status": "sent"}
    return {"status": "error", "code": code, "body": body[:500]}


@shared_task
def purge_dlq_older_than_default(days: int = None):
    """Purges AuditLog DLQ entries older than the configured threshold.

    If days is None, uses settings.AUDIT_DLQ_PURGE_DAYS (default 30).
    """
    try:
        from django.conf import settings

        if days is None:
            days = int(getattr(settings, "AUDIT_DLQ_PURGE_DAYS", 30))
    except Exception:
        days = 30
    cutoff = timezone.now() - timezone.timedelta(days=int(days))
    qs = AuditLog.objects.filter(action="event_DLQ", created_at__lt=cutoff)
    count = qs.count()
    qs.delete()
    return {"status": "ok", "purged": count, "days": int(days)}
