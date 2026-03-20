import logging
from datetime import datetime, timedelta, timezone as dt_tz

from django.utils import timezone

logger = logging.getLogger(__name__)


def on_reservation_confirmed_domotics(sender, instance, **kwargs):
    """
    When a reservation is confirmed, schedule lock code generation
    and temperature preset.

    Code generation: 48h before check-in (or immediately if <48h away).
    Temperature: 2h before check-in.
    """
    reservation = instance
    if not reservation or not getattr(reservation, "property_id", None):
        return

    try:
        from .tasks import generate_access_code_task, set_checkin_temperature_task

        now = timezone.now()

        prop = reservation.property
        checkin_dt = datetime.combine(
            reservation.check_in_date, prop.check_in_time,
        ).replace(tzinfo=dt_tz.utc)

        # Schedule lock code: 48h before or now if closer
        code_eta = checkin_dt - timedelta(hours=48)
        if code_eta <= now:
            generate_access_code_task.delay(reservation.id)
        else:
            generate_access_code_task.apply_async(
                args=[reservation.id], eta=code_eta,
            )

        # Schedule temperature: 2h before check-in
        temp_eta = checkin_dt - timedelta(hours=2)
        if temp_eta <= now:
            set_checkin_temperature_task.delay(reservation.id)
        else:
            set_checkin_temperature_task.apply_async(
                args=[reservation.id], eta=temp_eta,
            )
    except Exception:
        logger.debug("Domotics signal handler skipped for reservation %s", getattr(reservation, "id", "?"), exc_info=True)


def on_reservation_cancelled_domotics(sender, instance, **kwargs):
    """On cancellation, revoke access codes and reset temperature."""
    reservation = instance
    if not reservation or not getattr(reservation, "id", None):
        return

    try:
        from .tasks import reset_checkout_temperature_task, revoke_access_code_task

        revoke_access_code_task.delay(reservation.id)
        reset_checkout_temperature_task.delay(reservation.id)
    except Exception:
        logger.debug("Domotics cancel handler skipped for reservation %s", getattr(reservation, "id", "?"), exc_info=True)


def on_reservation_dates_changed_domotics(sender, instance, **kwargs):
    """When dates change, revoke old codes and reschedule for new dates."""
    reservation = instance
    if not reservation or not getattr(reservation, "id", None):
        return

    try:
        from .tasks import revoke_access_code_task

        revoke_access_code_task.delay(reservation.id)

        # Re-trigger confirmation flow for new dates
        on_reservation_confirmed_domotics(sender, instance, **kwargs)
    except Exception:
        logger.debug("Domotics dates-changed handler skipped for reservation %s", getattr(reservation, "id", "?"), exc_info=True)
