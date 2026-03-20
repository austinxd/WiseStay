from django.contrib import admin

from .models import LockAccessCode, NoiseAlert, SmartDevice, ThermostatLog


@admin.register(SmartDevice)
class SmartDeviceAdmin(admin.ModelAdmin):
    list_display = (
        "property", "display_name", "device_type", "brand",
        "status", "battery_level", "last_seen_at",
    )
    list_filter = ("device_type", "brand", "status")
    search_fields = ("property__name", "display_name", "external_device_id")
    readonly_fields = ("external_device_id", "api_credentials", "last_seen_at")


@admin.register(LockAccessCode)
class LockAccessCodeAdmin(admin.ModelAdmin):
    list_display = (
        "device", "reservation", "code_name", "status",
        "valid_from", "valid_until", "activated_at", "revoked_at",
    )
    list_filter = ("status",)
    search_fields = ("reservation__confirmation_code", "code_name")
    exclude = ("code",)  # Security: don't show access codes in admin


@admin.register(NoiseAlert)
class NoiseAlertAdmin(admin.ModelAdmin):
    list_display = (
        "device", "decibel_level", "severity", "duration_seconds",
        "alert_sent_to_owner", "alert_sent_to_guest", "created_at", "resolved_at",
    )
    list_filter = ("severity", "alert_sent_to_owner")
    readonly_fields = (
        "device", "reservation", "decibel_level", "threshold_exceeded",
        "severity", "duration_seconds", "alert_sent_to_owner",
        "alert_sent_to_guest", "resolved_at", "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ThermostatLog)
class ThermostatLogAdmin(admin.ModelAdmin):
    list_display = (
        "device", "event_type", "temperature_set_f", "mode",
        "triggered_by", "created_at",
    )
    list_filter = ("event_type", "triggered_by")
    readonly_fields = (
        "device", "event_type", "temperature_set_f", "mode",
        "triggered_by", "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
