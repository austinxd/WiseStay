from django.contrib import admin, messages

from .models import OwnerPayout, PaymentRecord, PayoutLineItem


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ("reservation", "payment_type", "status", "amount", "currency", "created_at")
    list_filter = ("status", "payment_type")
    search_fields = ("reservation__confirmation_code", "payment_intent_id")
    readonly_fields = (
        "reservation", "payment_type", "status", "amount", "currency",
        "payment_intent_id", "charge_id", "refund_id",
        "failure_reason", "receipt_url", "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class PayoutLineItemInline(admin.TabularInline):
    model = PayoutLineItem
    extra = 0
    readonly_fields = (
        "reservation", "reservation_total", "commission_amount",
        "owner_amount", "guest_name", "check_in_date", "check_out_date", "channel",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OwnerPayout)
class OwnerPayoutAdmin(admin.ModelAdmin):
    list_display = (
        "owner", "period_month", "period_year", "gross_revenue",
        "net_amount", "status", "paid_at",
    )
    list_filter = ("status", "period_year")
    search_fields = ("owner__email",)
    inlines = [PayoutLineItemInline]
    actions = ["approve_selected", "execute_approved"]

    @admin.action(description="Approve selected payouts")
    def approve_selected(self, request, queryset):
        from .payout_service import PayoutService

        approved = 0
        for payout in queryset.filter(status="draft"):
            try:
                PayoutService.approve_payout(payout.id, request.user.id)
                approved += 1
            except ValueError:
                pass
        self.message_user(request, f"Approved {approved} payout(s).", messages.SUCCESS)

    @admin.action(description="Execute approved payouts now")
    def execute_approved(self, request, queryset):
        from .tasks import execute_payouts_task

        execute_payouts_task.delay()
        self.message_user(request, "Payout execution dispatched.", messages.SUCCESS)


@admin.register(PayoutLineItem)
class PayoutLineItemAdmin(admin.ModelAdmin):
    list_display = ("payout", "guest_name", "reservation_total", "owner_amount", "channel")
    search_fields = ("guest_name",)
    readonly_fields = (
        "payout", "reservation", "reservation_total", "commission_amount",
        "owner_amount", "guest_name", "check_in_date", "check_out_date", "channel",
    )

    def has_add_permission(self, request):
        return False
