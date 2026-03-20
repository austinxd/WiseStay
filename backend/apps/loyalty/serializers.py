from decimal import Decimal

from rest_framework import serializers

from .models import PointTransaction, TierConfig


class PointTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointTransaction
        fields = [
            "id", "transaction_type", "points", "balance_after",
            "description", "created_at", "expires_at",
        ]
        read_only_fields = fields


class RedeemPointsSerializer(serializers.Serializer):
    points = serializers.IntegerField(min_value=1)
    reservation_id = serializers.IntegerField(required=False)


class CalculateDiscountSerializer(serializers.Serializer):
    base_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("1.00"),
    )


class ApplyReferralSerializer(serializers.Serializer):
    referral_code = serializers.CharField(max_length=20)


class TierConfigPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = TierConfig
        fields = [
            "tier_name", "min_reservations", "min_referrals",
            "discount_percent", "early_checkin", "late_checkout",
            "priority_support", "sort_order",
        ]
        read_only_fields = fields
