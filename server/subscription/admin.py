from django.contrib import admin

from .models import Subscription

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "type",
        "start_date",
        "end_date",
        "subscription_id",
        "created_at",
        "updated_at",
        "is_active",
    )
    list_filter = ("type", "start_date", "end_date", "is_active")
    search_fields = ("user__email", "subscription_id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    def is_active(self, obj):
        return obj.end_date is None or obj.end_date >= obj.updated_at

    is_active.boolean = True
    is_active.short_description = "Active?"
