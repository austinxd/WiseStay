import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def generate_upcoming_checkin_codes(self):
    """Hourly: generate codes for reservations checking in within 48h."""
    from apps.reservations.models import Reservation

    now = timezone.now()
    cutoff = now + timedelta(hours=48)

    reservations = (
        Reservation.objects.filter(
            status="confirmed",
            check_in_date__lte=cutoff.date(),
            check_in_date__gte=now.date(),
            property__smart_devices__device_type="smart_lock",
            property__smart_devices__status="online",
        )
        .exclude(lock_access_codes__status__in=["active", "scheduled"])
        .distinct()
    )

    from .services import DomoticsOrchestrator

    count = 0
    for reservation in reservations:
        try:
            result = DomoticsOrchestrator.generate_access_code_for_reservation(reservation.id)
            if result:
                count += 1
        except Exception as exc:
            logger.error("Code gen failed for reservation %s: %s", reservation.id, exc)

    logger.info("generate_upcoming_checkin_codes: generated %s codes", count)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def revoke_checkout_codes(self):
    """Hourly: revoke codes for checked-out reservations and expire old ones."""
    from apps.reservations.models import Reservation

    from .models import LockAccessCode
    from .services import DomoticsOrchestrator

    checked_out_ids = (
        Reservation.objects.filter(
            status="checked_out",
            lock_access_codes__status="active",
        )
        .values_list("id", flat=True)
        .distinct()
    )

    revoked = 0
    for res_id in checked_out_ids:
        try:
            revoked += DomoticsOrchestrator.revoke_access_code_for_reservation(res_id)
        except Exception as exc:
            logger.error("Revoke failed for reservation %s: %s", res_id, exc)

    now = timezone.now()
    expired = LockAccessCode.objects.filter(
        status="active",
        valid_until__lt=now,
    ).update(status="expired")

    logger.info("revoke_checkout_codes: revoked=%s, expired=%s", revoked, expired)


@shared_task(bind=True, max_retries=5, default_retry_delay=180)
def generate_access_code_task(self, reservation_id: int):
    """Generate access code for a specific reservation. Critical — 5 retries."""
    from .services import DomoticsOrchestrator

    try:
        result = DomoticsOrchestrator.generate_access_code_for_reservation(reservation_id)
        if result:
            logger.info("Access code generated for reservation %s", reservation_id)
    except Exception as exc:
        logger.error("generate_access_code_task failed for %s: %s", reservation_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def revoke_access_code_task(self, reservation_id: int):
    """Revoke codes for a specific reservation."""
    from .services import DomoticsOrchestrator

    try:
        DomoticsOrchestrator.revoke_access_code_for_reservation(reservation_id)
    except Exception as exc:
        logger.error("revoke_access_code_task failed for %s: %s", reservation_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def set_checkin_temperature_task(self, reservation_id: int):
    """Set comfort temperature before check-in."""
    from .services import DomoticsOrchestrator

    try:
        DomoticsOrchestrator.set_checkin_temperature(reservation_id)
    except Exception as exc:
        logger.error("set_checkin_temperature_task failed for %s: %s", reservation_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def reset_checkout_temperature_task(self, reservation_id: int):
    """Reset to eco mode after checkout."""
    from .services import DomoticsOrchestrator

    try:
        DomoticsOrchestrator.reset_checkout_temperature(reservation_id)
    except Exception as exc:
        logger.error("reset_checkout_temperature_task failed for %s: %s", reservation_id, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def process_seam_webhook_event(self, event_type: str, payload: dict):
    """Process a Seam webhook event."""
    from .models import LockAccessCode, SmartDevice
    from .services import DomoticsOrchestrator

    device_id = payload.get("device_id") or payload.get("data", {}).get("device_id", "")

    if event_type in ("device.connected", "device.disconnected"):
        status = "online" if event_type == "device.connected" else "offline"
        updated = SmartDevice.objects.filter(external_device_id=device_id).update(
            status=status, last_seen_at=timezone.now(),
        )
        if not updated:
            logger.warning("Seam webhook: device %s not found in WiseStay", device_id)
        return

    if event_type == "access_code.set_on_device":
        code_name = payload.get("data", {}).get("name", "")
        LockAccessCode.objects.filter(
            code_name=code_name, status="scheduled",
        ).update(status="active", activated_at=timezone.now())
        return

    if event_type == "access_code.removed_from_device":
        code_name = payload.get("data", {}).get("name", "")
        LockAccessCode.objects.filter(
            code_name=code_name, status="active",
        ).update(status="revoked", revoked_at=timezone.now())
        return

    if event_type == "noise_sensor.noise_threshold_triggered":
        data = payload.get("data", {})
        noise_db = data.get("noise_level_decibels", 0)
        duration = data.get("duration_seconds", 0)
        try:
            device = SmartDevice.objects.get(external_device_id=device_id)
            DomoticsOrchestrator.process_noise_alert(device.id, noise_db, duration)
        except SmartDevice.DoesNotExist:
            logger.warning("Seam noise webhook: device %s not found", device_id)
        return

    logger.debug("Seam webhook event '%s' not handled", event_type)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def refresh_all_device_statuses(self):
    """Periodic: refresh status of all active devices."""
    from .models import SmartDevice
    from .providers import get_lock_provider, get_noise_provider, get_thermostat_provider

    devices = SmartDevice.objects.filter(status__in=["online", "offline"])
    lock_p = get_lock_provider()
    therm_p = get_thermostat_provider()
    noise_p = get_noise_provider()

    updated = 0
    for device in devices:
        try:
            if device.device_type == "smart_lock":
                status = lock_p.get_lock_status(device.external_device_id)
            elif device.device_type == "thermostat":
                status = therm_p.get_status(device.external_device_id)
            elif device.device_type == "noise_sensor":
                status = noise_p.get_current_reading(device.external_device_id)
            else:
                continue

            device.last_seen_at = timezone.now()
            device.status = "online" if status.get("online", True) else "offline"
            battery = status.get("battery_level")
            if battery is not None:
                device.battery_level = int(battery * 100) if battery <= 1 else int(battery)
            device.save(update_fields=["last_seen_at", "status", "battery_level", "updated_at"])
            updated += 1
        except Exception:
            pass

    logger.info("refresh_all_device_statuses: updated %s/%s devices", updated, devices.count())
