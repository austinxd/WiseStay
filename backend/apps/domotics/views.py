import logging
from datetime import datetime, timedelta, timezone as dt_tz

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsGuest, IsOwner, IsOwnerOfProperty
from common.throttles import WebhookRateThrottle

from .models import LockAccessCode, NoiseAlert, SmartDevice, ThermostatLog
from .serializers import (
    DeviceOnboardSerializer,
    LockAccessCodeGuestSerializer,
    LockAccessCodeSerializer,
    NoiseAlertSerializer,
    SmartDeviceDetailSerializer,
    SmartDeviceSerializer,
    ThermostatControlSerializer,
)
from .tasks import process_seam_webhook_event

logger = logging.getLogger(__name__)


class PropertyDevicesView(APIView):
    """GET /properties/{property_id}/devices/ — list devices for a property."""

    permission_classes = [IsOwner | IsAdminUser]

    def get(self, request, property_id):
        from .services import DomoticsOrchestrator

        try:
            devices = DomoticsOrchestrator.get_property_devices_status(property_id)
        except Exception as exc:
            logger.error("Failed to get device statuses: %s", exc)
            devices = list(
                SmartDevice.objects.filter(property_id=property_id).values(
                    "id", "display_name", "device_type", "brand", "status",
                    "battery_level", "last_seen_at",
                )
            )
        return Response(devices)


class DeviceDetailView(APIView):
    """GET /devices/{device_id}/ — device detail with live status."""

    permission_classes = [IsOwner | IsAdminUser]

    def get(self, request, device_id):
        try:
            device = SmartDevice.objects.get(pk=device_id)
        except SmartDevice.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = SmartDeviceDetailSerializer(device)
        return Response(serializer.data)


class LockControlView(APIView):
    """POST /devices/{device_id}/lock/ or /unlock/"""

    permission_classes = [IsOwner | IsAdminUser]

    def post(self, request, device_id, action):
        try:
            device = SmartDevice.objects.get(pk=device_id, device_type="smart_lock")
        except SmartDevice.DoesNotExist:
            return Response({"error": "Lock not found"}, status=status.HTTP_404_NOT_FOUND)

        from .providers import get_lock_provider

        provider = get_lock_provider()
        try:
            if action == "lock":
                provider.lock(device.external_device_id)
            elif action == "unlock":
                provider.unlock(device.external_device_id)
            else:
                return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"status": "ok", "action": action, "device": device.display_name})


class ThermostatControlView(APIView):
    """POST /devices/{device_id}/temperature/"""

    permission_classes = [IsOwner | IsAdminUser]

    def post(self, request, device_id):
        try:
            device = SmartDevice.objects.get(pk=device_id, device_type="thermostat")
        except SmartDevice.DoesNotExist:
            return Response({"error": "Thermostat not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ThermostatControlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from decimal import Decimal

        from .providers import get_thermostat_provider

        provider = get_thermostat_provider()
        try:
            provider.set_temperature(
                device_id=device.external_device_id,
                heat_f=serializer.validated_data["heat_f"],
                cool_f=serializer.validated_data["cool_f"],
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        ThermostatLog.objects.create(
            device=device,
            event_type="setpoint_change",
            temperature_set_f=Decimal(str(serializer.validated_data["cool_f"])),
            mode="auto",
            triggered_by="owner",
        )
        return Response({"status": "ok", "device": device.display_name})


class ActiveAccessCodesView(generics.ListAPIView):
    """GET /properties/{property_id}/access-codes/ — masked codes for owner."""

    permission_classes = [IsOwner | IsAdminUser]
    serializer_class = LockAccessCodeSerializer

    def get_queryset(self):
        return LockAccessCode.objects.filter(
            device__property_id=self.kwargs["property_id"],
            status__in=["active", "scheduled"],
        ).select_related("device", "reservation").order_by("-valid_from")


class NoiseAlertsView(generics.ListAPIView):
    """GET /properties/{property_id}/noise-alerts/"""

    permission_classes = [IsOwner | IsAdminUser]
    serializer_class = NoiseAlertSerializer

    def get_queryset(self):
        qs = NoiseAlert.objects.filter(
            device__property_id=self.kwargs["property_id"],
        ).order_by("-created_at")
        severity = self.request.query_params.get("severity")
        if severity:
            qs = qs.filter(severity=severity)
        return qs


class GuestAccessInfoView(APIView):
    """GET /reservations/{reservation_id}/access/ — full codes for the guest."""

    permission_classes = [IsGuest]

    def get(self, request, reservation_id):
        from apps.reservations.models import Reservation

        try:
            reservation = Reservation.objects.select_related("property").get(
                pk=reservation_id,
                guest_user=request.user,
            )
        except Reservation.DoesNotExist:
            return Response({"error": "Reservation not found"}, status=status.HTTP_404_NOT_FOUND)

        if reservation.status not in ("confirmed", "checked_in"):
            return Response(
                {"error": "Access info only available for confirmed/active reservations"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Only show access info within 48h of check-in or during stay
        now = timezone.now()
        checkin_dt = datetime.combine(
            reservation.check_in_date, reservation.property.check_in_time,
        ).replace(tzinfo=dt_tz.utc)
        if now < checkin_dt - timedelta(hours=48):
            return Response(
                {"error": "Access info available 48 hours before check-in"},
                status=status.HTTP_403_FORBIDDEN,
            )

        codes = LockAccessCode.objects.filter(
            reservation=reservation,
            status__in=["active", "scheduled"],
        )

        prop = reservation.property
        instructions = prop.hostaway_raw_data.get("specialInstruction", "") if prop.hostaway_raw_data else ""

        return Response({
            "access_codes": LockAccessCodeGuestSerializer(codes, many=True).data,
            "check_in_time": prop.check_in_time.strftime("%H:%M"),
            "check_out_time": prop.check_out_time.strftime("%H:%M"),
            "instructions": instructions,
        })


class SeamWebhookView(APIView):
    """POST /webhooks/seam/ — receives Seam webhook events."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [WebhookRateThrottle]

    def post(self, request):
        payload = request.data
        if not isinstance(payload, dict):
            return Response({"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)

        event_type = payload.get("event_type") or payload.get("event", "")
        if not event_type:
            return Response({"status": "ignored"})

        process_seam_webhook_event.delay(event_type, payload)
        logger.info("Seam webhook dispatched: %s", event_type)
        return Response({"status": "accepted"})


class DeviceOnboardView(APIView):
    """POST /properties/{property_id}/devices/onboard/ — onboard from Seam."""

    permission_classes = [IsAdminUser]

    def post(self, request, property_id):
        serializer = DeviceOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .services import DomoticsOrchestrator

        try:
            device = DomoticsOrchestrator.sync_device_from_seam(
                seam_device_id=serializer.validated_data["seam_device_id"],
                property_id=property_id,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            SmartDeviceDetailSerializer(device).data,
            status=status.HTTP_201_CREATED,
        )
