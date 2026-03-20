from rest_framework import serializers

from .models import OwnerPayout, PaymentRecord, PayoutLineItem


class PaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRecord
        fields = [
            "id", "payment_type", "status", "amount", "currency",
            "receipt_url", "created_at",
        ]
        read_only_fields = fields


class PayoutLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutLineItem
        fields = [
            "id", "reservation_total", "commission_amount", "owner_amount",
            "guest_name", "check_in_date", "check_out_date", "channel",
        ]
        read_only_fields = fields


class OwnerPayoutListSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnerPayout
        fields = [
            "id", "period_month", "period_year", "gross_revenue",
            "commission_amount", "net_amount", "status", "paid_at",
        ]
        read_only_fields = fields


class OwnerPayoutDetailSerializer(serializers.ModelSerializer):
    line_items = PayoutLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = OwnerPayout
        fields = [
            "id", "period_month", "period_year", "gross_revenue",
            "commission_amount", "net_amount", "commission_rate_applied",
            "status", "approved_at", "paid_at", "stripe_transfer_id",
            "admin_notes", "line_items", "created_at",
        ]
        read_only_fields = fields


class StripeConnectOnboardSerializer(serializers.Serializer):
    return_url = serializers.URLField()
    refresh_url = serializers.URLField()
