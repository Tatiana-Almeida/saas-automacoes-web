from apps.auditing.models import AuditLog
from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.utils import timezone

from .models import Domain, Plan, Tenant


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "created_at")
    search_fields = ("code", "name")


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "schema_name",
        "plan",
        "plan_ref",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "schema_name")
    actions = ["reset_daily_counters"]

    def _daily_limits_for(self, tenant):
        plan_obj = getattr(tenant, "plan_ref", None)
        try:
            dl = getattr(plan_obj, "daily_limits", None)
            if isinstance(dl, dict):
                return dl
        except Exception:
            pass
        plan_code = getattr(plan_obj, "code", None) or getattr(tenant, "plan", "free")
        return settings.TENANT_PLAN_DAILY_LIMITS.get(plan_code, {})

    @admin.action(description="Reset daily plan counters for selected tenants")
    def reset_daily_counters(self, request, queryset):
        today = timezone.now().date().isoformat()
        total_keys = 0
        for tenant in queryset:
            schema = getattr(tenant, "schema_name", None)
            if not schema:
                continue
            daily_cfg = self._daily_limits_for(tenant)
            for category in daily_cfg.keys():
                key = f"plan_limit:{schema}:{category}:{today}"
                try:
                    cache.delete(key)
                    total_keys += 1
                except Exception:
                    # ignore errors to proceed with other tenants/categories
                    pass
        self.message_user(
            request,
            f"Daily counters reset for {queryset.count()} tenant(s), {total_keys} category keys cleared.",
        )
        try:
            # Audit entry for admin-triggered reset
            AuditLog.objects.create(
                user=getattr(request, "user", None),
                path="/admin/tenants/reset_daily_counters",
                method="ADMIN",
                ip_address=None,
            )
        except Exception:
            pass


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant")
    search_fields = ("domain",)
