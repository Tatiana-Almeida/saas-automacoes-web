from django.contrib import admin
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
import csv
from .models import AuditLog, AuditRetentionPolicy


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "method",
        "source",
        "action",
        "status_code",
        "tenant_schema",
        "path",
        "ip_address",
        "has_payload",
    )
    list_filter = ("method", "source", "action", "tenant_schema")
    search_fields = ("path", "user__username")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    readonly_fields = (
        "user",
        "path",
        "method",
        "source",
        "action",
        "status_code",
        "tenant_schema",
        "tenant_id",
        "ip_address",
        "created_at",
    )
    actions = ["export_selected_as_csv", "requeue_selected_dlq", "purge_old_dlq"]

    @admin.action(description="Export selected as CSV")
    def export_selected_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=audit_logs.csv"
        writer = csv.writer(response, quotechar="'", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            [
                "created_at",
                "username",
                "method",
                "source",
                "action",
                "status_code",
                "tenant_schema",
                "path",
                "ip_address",
                "payload",
            ]
        )
        for log in queryset.select_related("user"):
            try:
                import json

                payload_str = (
                    json.dumps(getattr(log, "payload", None), ensure_ascii=False)
                    if getattr(log, "payload", None) is not None
                    else ""
                )
            except Exception:
                payload_str = ""
            writer.writerow(
                [
                    log.created_at.isoformat(),
                    getattr(log.user, "username", ""),
                    log.method,
                    getattr(log, "source", ""),
                    getattr(log, "action", ""),
                    getattr(log, "status_code", "") or "",
                    getattr(log, "tenant_schema", "") or "",
                    log.path,
                    log.ip_address or "",
                    payload_str,
                ]
            )
        return response

    @admin.display(description="Payload")
    def has_payload(self, obj):
        return "✔" if getattr(obj, "payload", None) else "—"

    # Pretty JSON for payload (DLQ or other)
    def pretty_payload(self, obj):
        import json

        data = getattr(obj, "payload", None)
        if not data:
            return "-"
        try:
            pretty = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            pretty = str(data)
        return format_html(
            '<pre style="white-space: pre-wrap; max-width:100%; overflow:auto;">{}</pre>',
            pretty,
        )

    pretty_payload.short_description = "Payload"

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if "pretty_payload" not in base:
            base.append("pretty_payload")
        return tuple(base)

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if "pretty_payload" not in fields:
            fields.append("pretty_payload")
        return fields

    @admin.action(description="Requeue selected DLQ events")
    def requeue_selected_dlq(self, request, queryset):
        from apps.events.events import emit_event

        requeued = 0
        for log in queryset:
            try:
                if getattr(log, "action", None) != "event_DLQ":
                    continue
                path = getattr(log, "path", "") or ""
                # Expecting /events/DLQ/<EventName>
                parts = path.rstrip("/").split("/")
                if len(parts) < 4:
                    continue
                event_name = parts[-1]
                payload = getattr(log, "payload", None) or {}
                # Ensure tenant context and mark requeue
                payload.setdefault("tenant_schema", getattr(log, "tenant_schema", None))
                payload.setdefault("tenant_id", getattr(log, "tenant_id", None))
                payload["requeued_from_dlq"] = True
                emit_event(event_name, payload)
                requeued += 1
            except Exception:
                # Continue on errors to try others
                continue
        return HttpResponse(f"Requeued {requeued} DLQ event(s)")

    @admin.action(description="Purge DLQ older than N days (ignores selection)")
    def purge_old_dlq(self, request, queryset):
        days = getattr(settings, "AUDIT_DLQ_PURGE_DAYS", 30)
        cutoff = timezone.now() - timezone.timedelta(days=days)
        qs = AuditLog.objects.filter(action="event_DLQ", created_at__lt=cutoff)
        count = qs.count()
        qs.delete()
        return HttpResponse(f"Purged {count} DLQ log(s) older than {days} days")


class DLQFilter(SimpleListFilter):
    title = "DLQ"
    parameter_name = "dlq"

    def lookups(self, request, model_admin):
        return (("only", "Somente DLQ"),)

    def queryset(self, request, queryset):
        if self.value() == "only":
            return queryset.filter(action="event_DLQ")
        return queryset


AuditLogAdmin.list_filter = AuditLogAdmin.list_filter + (DLQFilter,)


@admin.register(AuditRetentionPolicy)
class AuditRetentionPolicyAdmin(admin.ModelAdmin):
    list_display = ("tenant_schema", "days")
    search_fields = ("tenant_schema",)
    ordering = ("tenant_schema",)
