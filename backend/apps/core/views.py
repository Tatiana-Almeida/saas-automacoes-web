from time import time
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .throttling import PlanScopedRateThrottle
from django.core.cache import cache
from apps.rbac.permissions import HasPermission
from django_redis import get_redis_connection
from django.db.models import Count
from apps.auditing.models import AuditLog
from saas_backend.celery import app as celery_app
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import hmac
import hashlib
from django.conf import settings
import logging
import json
from .webhooks import verify_hmac_signature, verify_stripe_signature
from .webhook_handlers import check_and_mark_idempotent, dispatch_webhook

class HealthView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Health check",
        description="Simple liveness probe for the API",
        responses={
            200: None,
        },
        examples=[
            OpenApiExample('ok', value={"status": "ok"}),
        ],
        tags=['core']
    )
    def get(self, request):
        return Response({"status": "ok"})


@method_decorator(cache_page(getattr(settings, 'CACHE_TTL_TENANT_STATUS', 0)), name='get')
class TenantThrottleStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary="Tenant throttle usage",
        description="Returns current throttle consumption for the authenticated tenant",
        tags=['core']
    )
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            return Response({"detail": "Tenant context unavailable"}, status=status.HTTP_400_BAD_REQUEST)

        schema = getattr(tenant, 'schema_name', 'public')
        # Prefer plan_ref.code when available
        plan_obj = getattr(tenant, 'plan_ref', None)
        plan = getattr(plan_obj, 'code', None) or getattr(tenant, 'plan', 'free')
        plan_rates = settings.TENANT_PLAN_THROTTLE_RATES.get(plan, {})

        throttle = PlanScopedRateThrottle()
        now_ts = int(time())
        scopes = []

        for scope, rate in plan_rates.items():
            num_requests, duration = throttle.parse_rate(rate)
            stats_key = PlanScopedRateThrottle.stats_cache_key(schema, scope)
            stats = throttle.cache.get(stats_key) or {}
            count = stats.get('count', 0)
            expires_at = stats.get('expires_at', 0)
            reset_in = max(expires_at - now_ts, 0)

            scopes.append({
                'scope': scope,
                'limit': num_requests,
                'window_seconds': duration,
                'used': min(count, num_requests),
                'remaining': max(num_requests - count, 0),
                'reset_in_seconds': reset_in,
            })

        # Daily plan limits
        def daily_limits_for(plan_code):
            # Prefer settings override when present, then fall back to model-based limits.
            cfg = settings.TENANT_PLAN_DAILY_LIMITS.get(plan_code, {})
            if isinstance(cfg, dict) and cfg:
                return cfg
            try:
                dl = getattr(plan_obj, 'daily_limits', None)
                if isinstance(dl, dict) and dl:
                    return dl
            except Exception:
                pass
            return cfg

        today = timezone.now().date().isoformat()
        daily_cfg = daily_limits_for(plan)
        daily = []
        for category, limit in daily_cfg.items():
            key = f"plan_limit:{schema}:{category}:{today}"
            used = int(throttle.cache.get(key, 0))
            remaining = max(int(limit) - used, 0) if isinstance(limit, int) else None
            daily.append({
                'category': category,
                'limit_per_day': limit,
                'used_today': used,
                'remaining_today': remaining,
            })

        return Response({
            'tenant': getattr(tenant, 'name', None),
            'schema': schema,
            'plan': plan,
            'scopes': scopes,
            'daily': daily,
        })


class ResetDailyPlanCountersView(APIView):
    permission_classes = [IsAuthenticated, HasPermission]
    required_permission = 'manage_tenants'

    @extend_schema(
        summary="Reset daily plan counters",
        description=(
            "Resets today's per-tenant daily counters for specified categories. "
            "If no categories are provided, resets all categories defined by the tenant's plan."
        ),
        tags=['core'],
        examples=[
            OpenApiExample(
                'Reset send_whatsapp',
                value={"categories": ["send_whatsapp"]}
            )
        ]
    )
    def post(self, request):
        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            return Response({"detail": "Tenant context unavailable"}, status=status.HTTP_400_BAD_REQUEST)

        schema = getattr(tenant, 'schema_name', 'public')
        plan_obj = getattr(tenant, 'plan_ref', None)
        plan = getattr(plan_obj, 'code', None) or getattr(tenant, 'plan', 'free')

        def daily_limits_for(plan_code):
            # Prefer settings override when present, then fall back to model-based limits.
            cfg = settings.TENANT_PLAN_DAILY_LIMITS.get(plan_code, {})
            if isinstance(cfg, dict) and cfg:
                return cfg
            try:
                dl = getattr(plan_obj, 'daily_limits', None)
                if isinstance(dl, dict) and dl:
                    return dl
            except Exception:
                pass
            return cfg

        daily_cfg = daily_limits_for(plan)
        req_data = getattr(request, 'data', {}) or {}
        categories = req_data.get('categories')
        if not categories:
            categories = list(daily_cfg.keys())

        today = timezone.now().date().isoformat()
        results = []
        for cat in categories:
            key = f"plan_limit:{schema}:{cat}:{today}"
            prev = int(cache.get(key, 0))
            try:
                cache.delete(key)
                results.append({
                    'category': cat,
                    'previous_used': prev,
                    'reset': True,
                })
            except Exception:
                results.append({
                    'category': cat,
                    'previous_used': prev,
                    'reset': False,
                })

        try:
            security_logger.info(
                'daily_counters_reset',
                extra={
                    'categories': categories,
                    'tenant_schema': schema,
                    'ip': getattr(request, 'META', {}).get('REMOTE_ADDR'),
                    'path': request.path,
                }
            )
        except Exception:
            pass

        return Response({
            'tenant': getattr(tenant, 'name', None),
            'schema': schema,
            'plan': plan,
            'categories_reset': results,
        }, status=status.HTTP_200_OK)


@method_decorator(cache_page(getattr(settings, 'CACHE_TTL_TENANT_DAILY_SUMMARY', 0)), name='get')
class TenantDailySummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary="Daily usage summary",
        description="Returns today's per-category usage and limits for the authenticated tenant",
        tags=['core']
    )
    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            return Response({"detail": "Tenant context unavailable"}, status=status.HTTP_400_BAD_REQUEST)

        schema = getattr(tenant, 'schema_name', 'public')
        plan_obj = getattr(tenant, 'plan_ref', None)
        plan = getattr(plan_obj, 'code', None) or getattr(tenant, 'plan', 'free')

        def daily_limits_for(plan_code):
            try:
                dl = getattr(plan_obj, 'daily_limits', None)
                if isinstance(dl, dict):
                    return dl
            except Exception:
                pass
            return settings.TENANT_PLAN_DAILY_LIMITS.get(plan_code, {})

        today = timezone.now().date().isoformat()
        daily_cfg = daily_limits_for(plan)
        logging.getLogger('apps.core').info('DAILY_CFG plan=%s cfg=%s', plan, daily_cfg)
        throttle = PlanScopedRateThrottle()

        summary = []
        warn_threshold = getattr(settings, 'TENANT_PLAN_DAILY_WARN_THRESHOLD', 80)
        for category, limit in daily_cfg.items():
            key = f"plan_limit:{schema}:{category}:{today}"
            used = int(throttle.cache.get(key, 0))
            percent_used = None
            try:
                if isinstance(limit, int) and limit > 0:
                    percent_used = round((used / int(limit)) * 100, 2)
            except Exception:
                percent_used = None
            near_limit = None
            try:
                if isinstance(percent_used, (int, float)) and isinstance(warn_threshold, int):
                    near_limit = percent_used >= warn_threshold
            except Exception:
                near_limit = None
            summary.append({
                'category': category,
                'limit_per_day': limit,
                'used_today': used,
                'remaining_today': max(int(limit) - used, 0) if isinstance(limit, int) else None,
                'percent_used_today': percent_used,
                'near_limit': near_limit,
                'threshold_percent': warn_threshold,
            })

        payload = {
            'tenant': getattr(tenant, 'name', None),
            'schema': schema,
            'plan': plan,
            'daily': summary,
        }
        logging.getLogger('apps.core').info('DAILY_SUMMARY payload=%s', payload)
        # Return raw JSON to avoid DRF renderer/caching interactions in tests
        return JsonResponse(payload)


class QueuesStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        summary="Queues and DLQ status",
        description="Reports Redis connectivity, Celery broker and eager mode, optional queue depths, and DLQ counts/recent entries.",
        tags=['core'],
        examples=[
            OpenApiExample('status', value={
                "redis": {"ok": True},
                "celery": {
                    "broker_url": "redis://localhost:6379/1",
                    "eager": False,
                    "queues": ["events", "dlq"],
                    "queue_depths": {"events": 0, "dlq": 0},
                    "workers": {"worker@host": {}},
                    "active": {"worker@host": []}
                },
                "dlq": {
                    "by_tenant": [{"tenant_schema": "acme", "count": 2}],
                    "recent": [{"id": 1, "tenant_schema": "acme", "path": "/events/DLQ/FailEvent", "created_at": "2025-12-18T12:00:00Z"}]
                }
            })
        ]
    )
    @swagger_auto_schema(
        operation_summary="Queues and DLQ status",
        responses={
            200: openapi.Response(
                description="Queue status",
                examples={
                    "application/json": {
                        "redis": {"ok": True},
                        "celery": {
                            "broker_url": "redis://localhost:6379/1",
                            "eager": False,
                            "queues": ["events", "dlq"],
                            "queue_depths": {"events": 0, "dlq": 0}
                        },
                        "dlq": {
                            "by_tenant": [{"tenant_schema": "acme", "count": 2}],
                            "recent": [{"id": 1, "tenant_schema": "acme", "path": "/events/DLQ/FailEvent", "created_at": "2025-12-18T12:00:00Z"}]
                        }
                    }
                }
            )
        },
        tags=['core']
    )
    def get(self, request):
        redis_info = {"ok": False}
        depths = {"events": None, "dlq": None}

        try:
            conn = get_redis_connection("default")
            redis_info["ok"] = bool(conn.ping())
            try:
                depths["events"] = int(conn.llen("events"))
            except Exception:
                pass
            try:
                depths["dlq"] = int(conn.llen("dlq"))
            except Exception:
                pass
        except Exception as e:
            redis_info["error"] = str(e)

        dlq_by_tenant = list(
            AuditLog.objects.filter(action='event_DLQ')
            .values('tenant_schema')
            .annotate(count=Count('id'))
            .order_by('-count')[:50]
        )
        recent_dlq = list(
            AuditLog.objects.filter(action='event_DLQ')
            .order_by('-created_at')
            .values('id', 'tenant_schema', 'path', 'created_at')[:5]
        )

        workers = None
        active = None
        try:
            insp = celery_app.control.inspect()
            workers = insp.registered() or insp.ping() or {}
            active = insp.active() or {}
        except Exception:
            pass

        payload = {
            "redis": redis_info,
            "celery": {
                "broker_url": getattr(settings, 'CELERY_BROKER_URL', None),
                "eager": getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False),
                "queues": ["events", "dlq"],
                "queue_depths": depths,
                "workers": workers,
                "active": active,
            },
            "dlq": {
                "by_tenant": dlq_by_tenant,
                "recent": recent_dlq,
            }
        }
        # Return raw JSON (bypass DRF renderer) so tests expecting top-level keys pass.
        return JsonResponse(payload)


security_logger = logging.getLogger('apps.security')

class WebhookReceiverView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Webhook receiver",
        description=(
            "Generic webhook endpoint with HMAC-SHA256 signature verification.\n"
            "Header `X-Signature` should contain the hex digest of HMAC(secret, raw_body).\n"
            "Optional header `X-Timestamp` (unix seconds) validated against `WEBHOOK_MAX_SKEW_SECONDS`.\n"
            "Secrets configured per provider in settings `WEBHOOK_SECRETS`."
        ),
        tags=['core']
    )
    @swagger_auto_schema(
        operation_summary="Receive provider webhook",
        manual_parameters=[
            openapi.Parameter('provider', openapi.IN_PATH, description='Provider key (e.g., stripe, paypal, custom)', type=openapi.TYPE_STRING),
            openapi.Parameter('X-Signature', openapi.IN_HEADER, description='Hex HMAC-SHA256 signature of raw body', type=openapi.TYPE_STRING),
            openapi.Parameter('X-Timestamp', openapi.IN_HEADER, description='Unix timestamp seconds for replay protection', type=openapi.TYPE_INTEGER),
        ],
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={'ok': openapi.Schema(type=openapi.TYPE_BOOLEAN)})},
        tags=['core']
    )
    def post(self, request, provider: str):
        secret = (getattr(settings, 'WEBHOOK_SECRETS', {}) or {}).get(provider)
        if not secret:
            return Response({'detail': 'Secret not configured'}, status=status.HTTP_501_NOT_IMPLEMENTED)

        raw = request.body or b''
        sig = request.headers.get('X-Signature') or request.headers.get('X-Hub-Signature-256')
        ts = request.headers.get('X-Timestamp')

        # Validate timestamp skew if provided
        if ts:
            try:
                ts = int(ts)
                now = int(time())
                max_skew = int(getattr(settings, 'WEBHOOK_MAX_SKEW_SECONDS', 300))
                if abs(now - ts) > max_skew:
                    return Response({'detail': 'Timestamp skew too large'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception:
                return Response({'detail': 'Invalid timestamp'}, status=status.HTTP_400_BAD_REQUEST)

        valid = False
        if provider == 'stripe':
            stripe_header = request.headers.get('Stripe-Signature')
            valid, stripe_ts = verify_stripe_signature(secret, raw, stripe_header or '')
            # Apply skew check using Stripe timestamp if header present
            if stripe_ts is not None:
                now = int(time())
                max_skew = int(getattr(settings, 'WEBHOOK_MAX_SKEW_SECONDS', 300))
                if abs(now - int(stripe_ts)) > max_skew:
                    return Response({'detail': 'Timestamp skew too large'}, status=status.HTTP_400_BAD_REQUEST)
            if stripe_header is None:
                return Response({'detail': 'Missing Stripe-Signature'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            if not sig:
                return Response({'detail': 'Missing signature'}, status=status.HTTP_401_UNAUTHORIZED)
            valid = verify_hmac_signature(secret, raw, sig)

        tenant = getattr(request, 'tenant', None)
        try:
            payload = None
            try:
                payload = json.loads(raw.decode('utf-8'))
            except Exception:
                payload = None
            security_logger.info(
                'webhook_received',
                extra={
                    'provider': provider,
                    'valid': valid,
                    'tenant_schema': getattr(tenant, 'schema_name', None),
                    'ip': getattr(request, 'META', {}).get('REMOTE_ADDR'),
                    'path': request.path,
                }
            )
            AuditLog.objects.create(
                user=None,
                path=request.path,
                method=request.method,
                source='webhook',
                action=f'webhook_{provider}',
                status_code=200 if valid else 401,
                tenant_schema=getattr(tenant, 'schema_name', None),
                tenant_id=getattr(tenant, 'id', None),
                ip_address=getattr(request, 'META', {}).get('REMOTE_ADDR'),
                payload=payload,
            )
        except Exception:
            pass

        if not valid:
            return Response({'detail': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)

        # Idempotency: detect event id
        event_id = None
        try:
            if provider == 'stripe' and isinstance(payload, dict):
                event_id = payload.get('id')
            else:
                event_id = request.headers.get('X-Event-Id') or (payload.get('id') if isinstance(payload, dict) else None)
        except Exception:
            event_id = None

        first_time = check_and_mark_idempotent(provider, event_id)

        # Dispatch provider-specific handler
        try:
            dispatch_webhook(
                provider,
                payload if isinstance(payload, dict) else {},
                getattr(tenant, 'schema_name', None),
                getattr(tenant, 'id', None),
            )
        except Exception:
            # Let event pipeline handle DLQ via its own mechanism
            pass

        return Response({'data': {'ok': True, 'idempotent': (not first_time)}})
