from rest_framework import serializers

from .models import LockAccessCode, NoiseAlert, SmartDevice, ThermostatLog


class SmartDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmartDevice
        fields = [
            "id", "device_type", "brand", "display_name", "status",
            "battery_level", "last_seen_at",
        ]
        read_only_fields = fields


class SmartDeviceDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmartDevice
        fields = [
            "id", "device_type", "brand", "model_name", "display_name",
            "status", "battery_level", "firmware_version", "config",
            "last_seen_at", "created_at",
        ]
        read_only_fields = fields


class LockAccessCodeSerializer(serializers.ModelSerializer):
    """For owners: code is masked."""

    masked_code = serializers.SerializerMethodField()

    class Meta:
        model = LockAccessCode
        fields = [
            "id", "code_name", "masked_code", "status",
            "valid_from", "valid_until", "activated_at", "revoked_at",
        ]
        read_only_fields = fields

    def get_masked_code(self, obj):
        if obj.code and len(obj.code) >= 2:
            return "*" * (len(obj.code) - 2) + obj.code[-2:]
        return "****"


class LockAccessCodeGuestSerializer(serializers.ModelSerializer):
    """For guests: code is fully visible."""

    class Meta:
        model = LockAccessCode
        fields = ["id", "code", "code_name", "valid_from", "valid_until", "status"]
        read_only_fields = fields


class NoiseAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoiseAlert
        fields = [
            "id", "decibel_level", "severity", "threshold_exceeded",
            "duration_seconds", "alert_sent_to_owner", "alert_sent_to_guest",
            "created_at", "resolved_at",
        ]
        read_only_fields = fields


class ThermostatControlSerializer(serializers.Serializer):
    heat_f = serializers.FloatField(min_value=55, max_value=85)
    cool_f = serializers.FloatField(min_value=60, max_value=90)

    def validate(self, data):
        if data["heat_f"] >= data["cool_f"]:
            raise serializers.ValidationError(
                "Heating setpoint must be less than cooling setpoint"
            )
        return data


class DeviceOnboardSerializer(serializers.Serializer):
    seam_device_id = serializers.CharField(max_length=100)


class GuestAccessInfoSerializer(serializers.Serializer):
    access_codes = LockAccessCodeGuestSerializer(many=True)
    check_in_time = serializers.TimeField()
    check_out_time = serializers.TimeField()
    instructions = serializers.CharField()
