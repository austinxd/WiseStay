from django.contrib import admin

from .models import HostawayCredential, SyncLog


@admin.register(HostawayCredential)
class HostawayCredentialAdmin(admin.ModelAdmin):
    list_display = ("client_id", "is_active", "token_expires_at", "created_at")
    list_filter = ("is_active",)
    readonly_fields = (
        "access_token",
        "refresh_token",
        "token_expires_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        # Singleton-like: only allow one active credential
        if HostawayCredential.objects.filter(is_active=True).exists():
            return False
        return super().has_add_permission(request)


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = (
        "sync_type",
        "status",
        "items_processed",
        "items_created",
        "items_updated",
        "items_failed",
        "triggered_by",
        "started_at",
        "completed_at",
    )
    list_filter = ("sync_type", "status", "triggered_by")
    readonly_fields = (
        "sync_type",
        "status",
        "items_processed",
        "items_created",
        "items_updated",
        "items_failed",
        "started_at",
        "completed_at",
        "error_message",
        "error_details",
        "triggered_by",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
