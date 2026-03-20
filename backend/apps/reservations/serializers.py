from datetime import date

from rest_framework import serializers

from .models import Reservation


class CheckAvailabilitySerializer(serializers.Serializer):
    property_id = serializers.IntegerField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()

    def validate(self, data):
        if data["check_out"] <= data["check_in"]:
            raise serializers.ValidationError("Check-out must be after check-in")
        if data["check_in"] < date.today():
            raise serializers.ValidationError("Check-in cannot be in the past")
        return data


class CalendarQuerySerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2024)


class PriceCalculationSerializer(serializers.Serializer):
    property_id = serializers.IntegerField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    points_to_redeem = serializers.IntegerField(min_value=0, required=False, default=0)

    def validate(self, data):
        if data["check_out"] <= data["check_in"]:
            raise serializers.ValidationError("Check-out must be after check-in")
        return data


class CreateBookingSerializer(serializers.Serializer):
    property_id = serializers.IntegerField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    guests_count = serializers.IntegerField(min_value=1)
    points_to_redeem = serializers.IntegerField(min_value=0, required=False, default=0)
    guest_notes = serializers.CharField(max_length=500, required=False, default="")

    def validate(self, data):
        if data["check_out"] <= data["check_in"]:
            raise serializers.ValidationError("Check-out must be after check-in")
        if data["check_in"] < date.today():
            raise serializers.ValidationError("Check-in cannot be in the past")
        return data


class CancelBookingSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, default="")


class ReservationListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    property_city = serializers.CharField(source="property.city", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id", "confirmation_code", "property_name", "property_city",
            "status", "channel", "check_in_date", "check_out_date", "nights",
            "total_amount", "discount_amount", "created_at",
        ]


class ReservationDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id", "confirmation_code", "property_name", "channel", "status",
            "check_in_date", "check_out_date", "nights", "guests_count",
            "guest_name", "guest_email",
            "nightly_rate", "cleaning_fee", "service_fee", "taxes",
            "total_amount", "discount_amount", "points_earned", "points_redeemed",
            "guest_notes", "confirmed_at", "cancelled_at",
            "checked_in_at", "checked_out_at", "created_at",
        ]
