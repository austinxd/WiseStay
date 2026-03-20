from django.db.models import Count
from rest_framework import serializers

from apps.domotics.models import NoiseAlert, SmartDevice
from apps.payments.models import OwnerPayout, PayoutLineItem
from apps.properties.models import Property, PropertyAmenity, PropertyImage
from apps.reservations.models import Reservation


# --- Properties ---

class OwnerPropertyListSerializer(serializers.ModelSerializer):
    cover_image_url = serializers.SerializerMethodField()
    active_reservations_count = serializers.IntegerField(read_only=True, default=0)
    devices_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Property
        fields = [
            "id", "name", "slug", "city", "state", "status", "property_type",
            "base_nightly_rate", "cover_image_url",
            "active_reservations_count", "devices_count",
        ]

    def get_cover_image_url(self, obj):
        img = getattr(obj, "_prefetched_cover", None)
        if img is None:
            cover = obj.images.filter(is_cover=True).first()
            return cover.url if cover else None
        return img


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ["id", "url", "caption", "sort_order", "is_cover"]


class PropertyAmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyAmenity
        fields = ["id", "name", "category"]


class OwnerPropertyDetailSerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)
    amenities = PropertyAmenitySerializer(many=True, read_only=True)

    class Meta:
        model = Property
        exclude = ["hostaway_raw_data", "hostaway_listing_id", "hostaway_last_synced_at"]


# --- Reservations ---

class OwnerReservationListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id", "confirmation_code", "guest_name", "guest_email",
            "property_name", "channel", "status",
            "check_in_date", "check_out_date", "nights",
            "total_amount", "created_at",
        ]


class OwnerReservationDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id", "confirmation_code", "guest_name", "guest_email", "guest_phone",
            "property_name", "channel", "status",
            "check_in_date", "check_out_date", "nights", "guests_count",
            "nightly_rate", "cleaning_fee", "service_fee", "taxes",
            "total_amount", "discount_amount",
            "guest_notes", "internal_notes",
            "confirmed_at", "cancelled_at", "checked_in_at", "checked_out_at",
            "created_at",
        ]


# --- Payouts ---

class PayoutLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutLineItem
        fields = [
            "guest_name", "check_in_date", "check_out_date", "channel",
            "reservation_total", "commission_amount", "owner_amount",
        ]


class OwnerPayoutListSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnerPayout
        fields = [
            "id", "period_month", "period_year", "gross_revenue",
            "commission_amount", "net_amount", "status", "paid_at",
        ]


class OwnerPayoutDetailSerializer(serializers.ModelSerializer):
    line_items = PayoutLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = OwnerPayout
        fields = [
            "id", "period_month", "period_year", "gross_revenue",
            "commission_amount", "net_amount", "commission_rate_applied",
            "status", "approved_at", "paid_at", "admin_notes",
            "line_items", "created_at",
        ]


# --- Profile ---

class OwnerProfileSerializer(serializers.Serializer):
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    company_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    commission_rate = serializers.DecimalField(max_digits=5, decimal_places=3, read_only=True)
    stripe_connected = serializers.BooleanField(read_only=True)
    is_payout_enabled = serializers.BooleanField(read_only=True)
    payout_day = serializers.IntegerField(read_only=True)


# --- Devices / Alerts ---

class OwnerDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmartDevice
        fields = ["id", "display_name", "device_type", "brand", "status", "battery_level", "last_seen_at"]


class OwnerNoiseAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoiseAlert
        fields = ["id", "decibel_level", "severity", "duration_seconds", "created_at", "resolved_at"]


# --- Query params ---

class OccupancyQuerySerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2024)


class RevenueQuerySerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2024)
    month = serializers.IntegerField(min_value=1, max_value=12, required=False)


class PerformanceQuerySerializer(serializers.Serializer):
    period = serializers.ChoiceField(choices=["month", "quarter", "ytd", "year", "all"], default="ytd")
