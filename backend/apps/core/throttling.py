from time import time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.throttling import ScopedRateThrottle


class PlanScopedRateThrottle(ScopedRateThrottle):
    """
    Scoped throttle that supports per-tenant plan-based rates.
    Uses the view's `throttle_scope` and, if available, overrides the rate based
    on `settings.TENANT_PLAN_THROTTLE_RATES[plan][scope]`.
    Cache key is namespaced by tenant schema to isolate tenants.
    """

    stats_prefix = "throttle_stats"

    def allow_request(self, request, view):
        # Stash request and view to access tenant in get_rate
        self._request = request
        self._view = view
        allowed = super().allow_request(request, view)
        if allowed:
            self.record_usage(request)
        return allowed

    def get_rate(self):
        plan_rates = getattr(settings, "TENANT_PLAN_THROTTLE_RATES", {})
        req = getattr(self, "_request", None)
        tenant = getattr(req, "tenant", None) if req is not None else None
        plan = getattr(tenant, "plan", None)
        # Prefer explicit per-plan rates
        if plan and self.scope:
            rate = plan_rates.get(plan, {}).get(self.scope)
            # Debug prints removed; keep logic intact
            if rate:
                return rate

        # Fallback: use REST_FRAMEWORK DEFAULT_THROTTLE_RATES if configured
        try:
            rf = getattr(settings, "REST_FRAMEWORK", None) or {}
            default_rates = rf.get("DEFAULT_THROTTLE_RATES", {})
            fallback = default_rates.get(self.scope)
            # Debug prints removed; keep fallback logic intact
            if fallback:
                return fallback
        except Exception:
            pass

        # Last resort: delegate to parent implementation; if parent raises
        # ImproperlyConfigured because there's no default rate for the
        # scope, swallow that and return None to disable DRF's exception
        # (interpreted as no throttling configured for this scope).
        try:
            return super().get_rate()
        except ImproperlyConfigured:
            return None

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        if ident is None:
            return None
        tenant = getattr(request, "tenant", None)
        schema = getattr(tenant, "schema_name", "public")
        scope = f"{self.scope}:{schema}" if self.scope else f":{schema}"
        return self.cache_format % {
            "scope": scope,
            "ident": ident,
        }

    @classmethod
    def stats_cache_key(cls, schema, scope):
        scope = scope or "default"
        return f"{cls.stats_prefix}:{schema}:{scope}"

    def record_usage(self, request):
        tenant = getattr(request, "tenant", None)
        schema = getattr(tenant, "schema_name", "public")
        scope = self.scope or "default"
        key = self.stats_cache_key(schema, scope)
        # Use separate keys and cache atomic increment when available (Redis).
        current = int(time())
        window = getattr(self, "duration", None) or 60
        count_key = f"{key}:count"
        exp_key = f"{key}:exp"
        try:
            expires_at = int(self.cache.get(exp_key) or 0)
        except Exception:
            expires_at = 0

        if expires_at <= current:
            # Initialize window: set count=1 and expiry atomically where possible
            try:
                # cache.add will only set if not present
                self.cache.add(count_key, 1, timeout=window)
                self.cache.set(exp_key, current + window, timeout=window)
            except Exception:
                # Fallback to dict-style storage if atomic ops unavailable
                data = {"count": 1, "expires_at": current + window}
                self.cache.set(key, data, timeout=window)
        else:
            # Window active: increment atomically if supported
            try:
                self.cache.incr(count_key)
            except Exception:
                # Fallback to dict-style read/modify/write
                try:
                    data = self.cache.get(key) or {"count": 0, "expires_at": expires_at}
                    data["count"] = int(data.get("count", 0)) + 1
                    data["expires_at"] = expires_at
                    self.cache.set(key, data, timeout=max(0, expires_at - current))
                except Exception:
                    pass
