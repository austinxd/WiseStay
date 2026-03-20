from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import GuestProfile, OwnerProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "phone",
        "phone_verified",
        "email_verified",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "is_active", "is_staff", "phone_verified", "email_verified")

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "WiseStay",
            {
                "fields": ("role", "phone", "phone_verified", "email_verified", "avatar_url"),
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "WiseStay",
            {
                "fields": ("role", "phone"),
            },
        ),
    )


@admin.register(GuestProfile)
class GuestProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "loyalty_tier",
        "points_balance",
        "direct_bookings_count",
        "referral_code",
    )
    list_filter = ("loyalty_tier",)
    readonly_fields = ("referral_code", "created_at", "updated_at")


@admin.register(OwnerProfile)
class OwnerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "company_name",
        "commission_rate",
        "payout_day",
        "is_payout_enabled",
    )
    list_filter = ("is_payout_enabled",)
    readonly_fields = ("created_at", "updated_at")
