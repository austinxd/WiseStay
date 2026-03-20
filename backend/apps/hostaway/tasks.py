import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_listings_task(self):
    """Periodic sync of all Hostaway listings. Runs every 6 hours."""
    from .sync import HostawaySyncEngine

    try:
        engine = HostawaySyncEngine(triggered_by="celery")
        sync_log = engine.sync_all_listings()
        logger.info("sync_listings_task completed: %s", sync_log.status)
    except Exception as exc:
        logger.error("sync_listings_task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_reservations_task(self):
    """Periodic sync of modified reservations. Runs every 15 minutes."""
    from .sync import HostawaySyncEngine

    try:
        engine = HostawaySyncEngine(triggered_by="celery")
        sync_log = engine.sync_reservations()
        logger.info("sync_reservations_task completed: %s", sync_log.status)
    except Exception as exc:
        logger.error("sync_reservations_task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_calendar_task(self, property_id=None):
    """Periodic sync of calendar availability. Runs every 2 hours."""
    from .sync import HostawaySyncEngine

    try:
        engine = HostawaySyncEngine(triggered_by="celery")
        sync_log = engine.sync_calendar(property_id=property_id)
        logger.info("sync_calendar_task completed: %s", sync_log.status)
    except Exception as exc:
        logger.error("sync_calendar_task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_webhook_event(self, event_type: str, payload: dict):
    """
    Process a Hostaway webhook event asynchronously.
    Dispatches to the correct processor based on event_type.
    """
    from . import webhooks

    processors = {
        "reservation_created": webhooks.process_reservation_created,
        "reservation_updated": webhooks.process_reservation_updated,
        "message_received": webhooks.process_message_received,
    }

    processor = processors.get(event_type)
    if not processor:
        logger.warning("Unknown webhook event type: %s", event_type)
        return

    try:
        processor(payload)
        logger.info("Webhook event '%s' processed successfully", event_type)
    except Exception as exc:
        logger.error("Webhook event '%s' failed: %s", event_type, exc, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=5, default_retry_delay=120)
def push_reservation_to_hostaway(self, reservation_id: int):
    """
    Push a direct reservation to Hostaway after Stripe payment confirmation.
    More retries (5) because it's critical that Hostaway blocks the calendar.
    """
    from .sync import HostawaySyncEngine

    try:
        engine = HostawaySyncEngine(triggered_by="celery")
        ha_id = engine.push_direct_reservation_to_hostaway(reservation_id)
        logger.info(
            "Reservation %s pushed to Hostaway as %s",
            reservation_id, ha_id,
        )
    except Exception as exc:
        logger.error(
            "Failed to push reservation %s to Hostaway (attempt %s/%s): %s",
            reservation_id, self.request.retries + 1, self.max_retries, exc,
        )
        raise self.retry(exc=exc)
