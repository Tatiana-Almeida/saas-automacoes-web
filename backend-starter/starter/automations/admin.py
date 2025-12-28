from django.contrib import admin

from .models import Automation, AutomationLog


@admin.register(Automation)
class AutomationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "type",
        "is_active",
        "last_run_at",
        "last_status",
        "created_at",
    )
    list_filter = ("type", "is_active", "last_status")
    search_fields = ("name", "user__email")


@admin.register(AutomationLog)
class AutomationLogAdmin(admin.ModelAdmin):
    list_display = ("automation", "status", "created_at", "started_at", "finished_at")
    list_filter = ("status", "created_at")
    readonly_fields = (
        "automation",
        "status",
        "error_message",
        "output_payload",
        "started_at",
        "finished_at",
        "created_at",
    )
