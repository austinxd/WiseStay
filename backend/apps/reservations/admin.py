from django.contrib import admin

from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "confirmation_code", "property", "guest_name", "channel",
        "status", "check_in_date", "check_out_date", "total_amount",
    )
    list_filter = ("status", "channel", "check_in_date")
    search_fields = ("confirmation_code", "guest_name", "guest_email")
    date_hierarchy = "check_in_date"
    readonly_fields = (
        "stripe_payment_intent_id", "hostaway_reservation_id",
        "confirmed_at", "cancelled_at", "checked_in_at", "checked_out_at",
        "points_earned", "points_redeemed",
    )
