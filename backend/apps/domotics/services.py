import logging
import secrets
from datetime import datetime, timedelta, timezone as dt_tz
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.properties.models import Property
from apps.reservations.models import Reservation

from .exceptions import AccessCodeError, DeviceNotFoundError, DomoticsProviderError
from .models import LockAccessCode, NoiseAlert, SmartDevice, ThermostatLog
from .providers import get_lock_provider, get_noise_provider, get_thermostat_provider

logger = logging.getLogger(__name__)

# Trivial codes to exclude from generation
TRIVIAL_CODES = {
    "000000", "111111", "222222", "333333", "444444",
    "555555", "666666", "777777", "888888", "999999",
    "123456", "654321", "000001", "012345",
}

# Temperature defaults
DEFAULT_COOL_F = 72.0
DEFAULT_HEAT_F = 68.0
ECO_COOL_F = 78.0
ECO_HEAT_F = 60.0

GUEST_TEMP_PRESETS = {
    "cool": {"cool_f": 70.0, "heat_f": 66.0},
    "warm": {"cool_f": 76.0, "heat_f": 72.0},
}


def _generate_code(length: int = 6) -> str:
    """Generate a random numeric code, excluding trivial patterns."""
    while True:
        code = "".join(secrets.choice("0123456789") for _ in range(length))
        if code not in TRIVIAL_CODES:
            return code


def _make_aware_dt(dt_date, time_obj) -> datetime:
    """Combine a date and time into a timezone-aware datetime (UTC)."""
    naive = datetime.combine(dt_date, time_obj)
    return naive.replace(tzinfo=dt_tz.utc)


class DomoticsOrchestrator:

    @staticmethod
    def generate_access_code_for_reservation(reservation_id: int) -> LockAccessCode | None:
        reservation = Reservation.objects.select_related(
            "property", "guest_user",
        ).get(pk=reservation_id)

        if reservation.status not in ("confirmed", "checked_in"):
            logger.info("Skipping code gen: reservation %s status=%s", reservation_id, reservation.status)
            return None

        prop = reservation.property
        locks = SmartDevice.objects.filter(
            property=prop,
            device_type="smart_lock",
            status="online",
        )

        if not locks.exists():
            logger.info("No online locks for property %s", prop.id)
            return None

        valid_from = _make_aware_dt(reservation.check_in_date, prop.check_in_time)
        valid_until = _make_aware_dt(reservation.check_out_date, prop.check_out_time)

        provider = get_lock_provider()
        primary_code = None

        for lock in locks:
            # Skip if code already exists for this reservation+device
            existing = LockAccessCode.objects.filter(
                device=lock,
                reservation=reservation,
                status__in=["active", "scheduled"],
            ).exists()
            if existing:
                logger.info("Code already exists for reservation %s + device %s", reservation_id, lock.id)
                continue

            code = _generate_code()
            code_name = f"WS-{reservation.confirmation_code} {lock.display_name}"[:100]

            access_code = LockAccessCode.objects.create(
                device=lock,
                reservation=reservation,
                code=code,
                code_name=code_name,
                status="scheduled",
                valid_from=valid_from,
                valid_until=valid_until,
            )

            try:
                result = provider.create_access_code(
                    device_id=lock.external_device_id,
                    code=code,
                    name=code_name,
                    starts_at=valid_from,
                    ends_at=valid_until,
                )
                access_code.status = "active"
                access_code.activated_at = timezone.now()
                access_code.save(update_fields=["status", "activated_at", "updated_at"])
                logger.info(
                    "Access code created for reservation %s, device %s",
                    reservation.confirmation_code, lock.display_name,
                )
            except (AccessCodeError, DomoticsProviderError) as exc:
                access_code.status = "failed"
                access_code.error_message = str(exc)
                access_code.retry_count += 1
                access_code.save(update_fields=["status", "error_message", "retry_count", "updated_at"])
                logger.error(
                    "Failed to create access code for reservation %s, device %s: %s",
                    reservation.confirmation_code, lock.display_name, exc,
                )

            if primary_code is None:
                primary_code = access_code

        return primary_code

    @staticmethod
    def revoke_access_code_for_reservation(reservation_id: int) -> int:
        codes = LockAccessCode.objects.filter(
            reservation_id=reservation_id,
            status__in=["active", "scheduled"],
        ).select_related("device")

        provider = get_lock_provider()
        revoked_count = 0

        for code in codes:
            try:
                provider.delete_access_code(
                    device_id=code.device.external_device_id,
                    external_code_id=code.code_name,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to revoke code %s via provider (will expire by valid_until): %s",
                    code.code_name, exc,
                )

            code.status = "revoked"
            code.revoked_at = timezone.now()
            code.save(update_fields=["status", "revoked_at", "updated_at"])
            revoked_count += 1

        if revoked_count:
            logger.info("Revoked %s access codes for reservation %s", revoked_count, reservation_id)
        return revoked_count

    @staticmethod
    def set_checkin_temperature(reservation_id: int) -> bool:
        reservation = Reservation.objects.select_related(
            "property", "guest_user",
        ).get(pk=reservation_id)

        thermostats = SmartDevice.objects.filter(
            property=reservation.property,
            device_type="thermostat",
            status="online",
        )

        if not thermostats.exists():
            return False

        cool_f = DEFAULT_COOL_F
        heat_f = DEFAULT_HEAT_F

        # Check guest temperature preferences
        if reservation.guest_user:
            try:
                profile = reservation.guest_user.guest_profile
                prefs = profile.preferences or {}
                temp_pref = prefs.get("temperature_preference")
                if temp_pref:
                    if temp_pref in GUEST_TEMP_PRESETS:
                        cool_f = GUEST_TEMP_PRESETS[temp_pref]["cool_f"]
                        heat_f = GUEST_TEMP_PRESETS[temp_pref]["heat_f"]
                    elif isinstance(temp_pref, (int, float)):
                        cool_f = float(temp_pref) + 2
                        heat_f = float(temp_pref) - 2
            except Exception:
                pass  # use defaults

        # Check property config overrides
        for therm in thermostats:
            device_cool = therm.config.get("default_cool_f", cool_f)
            device_heat = therm.config.get("default_heat_f", heat_f)

        provider = get_thermostat_provider()
        success = False

        for therm in thermostats:
            try:
                provider.set_temperature(
                    device_id=therm.external_device_id,
                    heat_f=heat_f,
                    cool_f=cool_f,
                )
                ThermostatLog.objects.create(
                    device=therm,
                    event_type="checkin_preset",
                    temperature_set_f=Decimal(str(cool_f)),
                    mode="auto",
                    triggered_by="system",
                )
                success = True
                logger.info(
                    "Checkin temperature set for reservation %s: cool=%.1f heat=%.1f",
                    reservation_id, cool_f, heat_f,
                )
            except DomoticsProviderError as exc:
                logger.error("Failed to set checkin temp for device %s: %s", therm.id, exc)

        return success

    @staticmethod
    def reset_checkout_temperature(reservation_id: int) -> bool:
        reservation = Reservation.objects.select_related("property").get(pk=reservation_id)

        thermostats = SmartDevice.objects.filter(
            property=reservation.property,
            device_type="thermostat",
            status="online",
        )

        if not thermostats.exists():
            return False

        provider = get_thermostat_provider()
        success = False

        for therm in thermostats:
            eco_cool = therm.config.get("away_cool_f", ECO_COOL_F)
            eco_heat = therm.config.get("away_heat_f", ECO_HEAT_F)

            try:
                provider.set_temperature(
                    device_id=therm.external_device_id,
                    heat_f=eco_heat,
                    cool_f=eco_cool,
                )
                provider.set_mode(therm.external_device_id, "eco")
                ThermostatLog.objects.create(
                    device=therm,
                    event_type="checkout_reset",
                    temperature_set_f=Decimal(str(eco_cool)),
                    mode="eco",
                    triggered_by="system",
                )
                success = True
                logger.info("Checkout temp reset for reservation %s", reservation_id)
            except DomoticsProviderError as exc:
                logger.error("Failed to reset temp for device %s: %s", therm.id, exc)

        return success

    @staticmethod
    def process_noise_alert(
        device_id: int,
        decibel_level: float,
        duration_seconds: int = 0,
    ) -> NoiseAlert | None:
        try:
            device = SmartDevice.objects.select_related("property").get(pk=device_id)
        except SmartDevice.DoesNotExist:
            logger.error("Noise alert for unknown device %s", device_id)
            return None

        threshold = float(device.config.get("noise_threshold_db", 70))

        if decibel_level <= threshold:
            return None

        if duration_seconds > 900 or decibel_level > 85:
            severity = "critical"
        else:
            severity = "warning"

        # Find active reservation for this property
        now = timezone.now().date()
        reservation = Reservation.objects.filter(
            property=device.property,
            status="checked_in",
            check_in_date__lte=now,
            check_out_date__gte=now,
        ).first()

        alert = NoiseAlert.objects.create(
            device=device,
            reservation=reservation,
            decibel_level=Decimal(str(decibel_level)),
            threshold_exceeded=True,
            severity=severity,
            duration_seconds=duration_seconds,
            alert_sent_to_owner=True,  # TODO: integrate actual notification
        )

        if severity == "critical":
            alert.alert_sent_to_guest = True
            alert.save(update_fields=["alert_sent_to_guest"])

        logger.info(
            "Noise alert created: %.1f dB (%s) on property %s",
            decibel_level, severity, device.property.name,
        )
        return alert

    @staticmethod
    def get_property_devices_status(property_id: int) -> list[dict]:
        devices = SmartDevice.objects.filter(property_id=property_id)
        results = []

        lock_provider = get_lock_provider()
        therm_provider = get_thermostat_provider()
        noise_provider = get_noise_provider()

        for device in devices:
            info = {
                "device_id": device.id,
                "display_name": device.display_name,
                "device_type": device.device_type,
                "brand": device.brand,
                "status": device.status,
                "battery_level": device.battery_level,
                "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
            }

            try:
                if device.device_type == "smart_lock":
                    status = lock_provider.get_lock_status(device.external_device_id)
                    info["locked"] = status.get("locked")
                    _update_device_status(device, status)
                elif device.device_type == "thermostat":
                    status = therm_provider.get_status(device.external_device_id)
                    info["temperature_f"] = status.get("temperature_f")
                    _update_device_status(device, status)
                elif device.device_type == "noise_sensor":
                    status = noise_provider.get_current_reading(device.external_device_id)
                    info["noise_level_db"] = status.get("decibel_level")
                    _update_device_status(device, status)
            except DomoticsProviderError:
                info["status"] = "error"

            results.append(info)

        return results

    @staticmethod
    def sync_device_from_seam(seam_device_id: str, property_id: int) -> SmartDevice:
        from .providers.seam_provider import SeamProvider

        provider = SeamProvider()
        data = provider.get_device(seam_device_id)

        device_type_raw = data.get("device_type", "").lower()
        if "lock" in device_type_raw:
            device_type = "smart_lock"
        elif "thermostat" in device_type_raw:
            device_type = "thermostat"
        elif "noise" in device_type_raw or "minut" in device_type_raw:
            device_type = "noise_sensor"
        else:
            device_type = "smart_lock"  # default

        manufacturer = data.get("manufacturer", "").lower()
        brand_map = {
            "august": "august", "schlage": "schlage",
            "nest": "nest", "google": "nest",
            "ecobee": "ecobee", "minut": "minut",
        }
        brand = brand_map.get(manufacturer, "august")

        device, created = SmartDevice.objects.update_or_create(
            external_device_id=seam_device_id,
            defaults={
                "property_id": property_id,
                "device_type": device_type,
                "brand": brand,
                "model_name": data.get("model", ""),
                "display_name": data.get("name", "") or f"{brand.title()} {device_type}",
                "status": "online" if data.get("online") else "offline",
                "battery_level": int(data["battery_level"] * 100) if data.get("battery_level") else None,
                "last_seen_at": timezone.now(),
            },
        )

        action = "Created" if created else "Updated"
        logger.info("%s device %s from Seam (property %s)", action, device.display_name, property_id)
        return device


def _update_device_status(device: SmartDevice, status: dict):
    """Update device model with latest status from provider."""
    device.last_seen_at = timezone.now()
    online = status.get("online", True)
    device.status = "online" if online else "offline"
    battery = status.get("battery_level")
    if battery is not None:
        device.battery_level = int(battery * 100) if battery <= 1 else int(battery)
    device.save(update_fields=["last_seen_at", "status", "battery_level", "updated_at"])
