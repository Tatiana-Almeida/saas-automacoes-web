from django.contrib import admin

from .models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "status", "email", "user", "created_at")
    list_filter = ("status",)
    search_fields = ("subject", "message", "email")
