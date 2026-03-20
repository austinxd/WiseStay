from django.contrib import admin, messages

from .models import PointTransaction, Referral, TierConfig, TierHistory


@admin.register(TierConfig)
class TierConfigAdmin(admin.ModelAdmin):
    list_display = (
        "tier_name",
        "min_reservations",
        "min_referrals",
        "discount_percent",
        "bonus_points_on_upgrade",
        "early_checkin",
        "late_checkout",
        "priority_support",
        "is_active",
        "sort_order",
    )
    list_editable = (
        "min_reservations",
        "min_referrals",
        "discount_percent",
        "bonus_points_on_upgrade",
        "is_active",
        "sort_order",
    )
    ordering = ("sort_order",)
    actions = ["recalculate_all_guest_tiers"]

    @admin.action(description="Recalculate tiers for ALL guests (async)")
    def recalculate_all_guest_tiers(self, request, queryset):
        from .tasks import recalculate_all_tiers

        recalculate_all_tiers.delay()
        self.message_user(
            request,
            "Tier recalculation dispatched. Check Celery logs for results.",
            messages.SUCCESS,
        )


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "guest_email",
        "transaction_type",
        "points",
        "balance_after",
        "description",
        "created_at",
        "expires_at",
    )
    list_filter = ("transaction_type", "created_at")
    search_fields = ("guest__email",)
    readonly_fields = (
        "guest",
        "reservation",
        "transaction_type",
        "points",
        "expires_at",
        "points_remaining",
        "balance_after",
        "description",
        "created_at",
        "updated_at",
    )
    actions = ["grant_adjustment_points"]

    def guest_email(self, obj):
        return obj.guest.email

    guest_email.short_description = "Guest"
    guest_email.admin_order_field = "guest__email"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Grant 50 adjustment points to selected guests")
    def grant_adjustment_points(self, request, queryset):
        from django.db import transaction

        from apps.accounts.models import GuestProfile

        guest_ids = set(queryset.values_list("guest_id", flat=True))
        granted = 0

        for guest_id in guest_ids:
            try:
                with transaction.atomic():
                    profile = GuestProfile.objects.select_for_update().get(
                        user_id=guest_id,
                    )
                    new_balance = profile.points_balance + 50
                    PointTransaction.objects.create(
                        guest_id=guest_id,
                        transaction_type="adjust",
                        points=50,
                        balance_after=new_balance,
                        description="Admin adjustment via Django Admin",
                    )
                    profile.points_balance = new_balance
                    profile.save(update_fields=["points_balance", "updated_at"])
                    granted += 1
            except Exception:
                pass

        self.message_user(
            request,
            f"Granted 50 points to {granted} guest(s).",
            messages.SUCCESS,
        )


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = (
        "referrer",
        "referred_user",
        "referral_code_used",
        "status",
        "reward_points_granted",
        "created_at",
        "completed_at",
    )
    list_filter = ("status",)
    search_fields = ("referrer__email", "referred_user__email")


@admin.register(TierHistory)
class TierHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "guest_email",
        "previous_tier",
        "new_tier",
        "triggered_by",
        "created_at",
    )
    list_filter = ("triggered_by", "new_tier")
    search_fields = ("guest__email",)
    readonly_fields = (
        "guest",
        "previous_tier",
        "new_tier",
        "reason",
        "triggered_by",
        "created_at",
        "updated_at",
    )

    def guest_email(self, obj):
        return obj.guest.email

    guest_email.short_description = "Guest"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
