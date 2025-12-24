from django.contrib import admin
from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__email", "plan")
