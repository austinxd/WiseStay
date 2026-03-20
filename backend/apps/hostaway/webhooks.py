import logging

from django.db import transaction

from apps.accounts.models import User
from apps.chatbot.models import Conversation, Message
from apps.properties.models import Property
from apps.reservations.models import Reservation

from .mappers import map_reservation_to_model
from .models import SyncLog
from .signals import reservation_cancelled, reservation_confirmed, reservation_dates_changed

logger = logging.getLogger(__name__)


def process_reservation_created(payload: dict):
    """
    Process a reservationCreated webhook event.

    Idempotent: if the reservation already exists, treats as update.
    Always returns without raising — errors are logged internally.
    """
    res_data = payload.get("data") or payload
    ha_id = str(res_data.get("id", ""))
    if not ha_id:
        logger.error("Webhook reservationCreated missing reservation id in payload")
        return

    # Check if reservation already exists (idempotency)
    existing = Reservation.objects.filter(hostaway_reservation_id=ha_id).first()
    if existing:
        logger.info("Reservation %s already exists — treating as update", ha_id)
        process_reservation_updated(payload)
        return

    # Resolve property
    listing_id = str(res_data.get("listingMapId", ""))
    prop = Property.objects.filter(hostaway_listing_id=listing_id).first()
    if not prop:
        logger.error(
            "Webhook: no local property for Hostaway listing %s (reservation %s)",
            listing_id, ha_id,
        )
        SyncLog.objects.create(
            sync_type="reservations",
            status="failed",
            triggered_by="webhook",
            error_message=f"No local property for listing {listing_id}",
            items_processed=1,
            items_failed=1,
        )
        return

    mapped = map_reservation_to_model(res_data)
    if not mapped:
        logger.error("Webhook: mapper returned empty for reservation %s", ha_id)
        return

    mapped["property_id"] = prop.id

    # Try to match guest user by email
    guest_email = mapped.get("guest_email", "")
    if guest_email:
        guest_user = User.objects.filter(
            email__iexact=guest_email, role="guest", is_active=True
        ).first()
        if guest_user:
            mapped["guest_user_id"] = guest_user.id

    # Ensure unique confirmation_code
    code = mapped.get("confirmation_code", ha_id)
    if Reservation.objects.filter(confirmation_code=code).exists():
        code = f"HA-{ha_id}"
        mapped["confirmation_code"] = code

    try:
        with transaction.atomic():
            reservation = Reservation.objects.create(**mapped)

        logger.info(
            "Webhook: created reservation %s (channel=%s, property=%s)",
            reservation.confirmation_code, reservation.channel, prop.name,
        )

        if reservation.status in ("confirmed", "checked_in"):
            reservation_confirmed.send(
                sender=Reservation, instance=reservation, created=True,
            )
    except Exception:
        logger.exception("Webhook: failed to create reservation %s", ha_id)


def process_reservation_updated(payload: dict):
    """
    Process a reservationUpdated webhook event.

    If the reservation doesn't exist locally, treats as created (idempotency).
    """
    res_data = payload.get("data") or payload
    ha_id = str(res_data.get("id", ""))
    if not ha_id:
        logger.error("Webhook reservationUpdated missing reservation id")
        return

    existing = Reservation.objects.filter(hostaway_reservation_id=ha_id).first()
    if not existing:
        logger.info("Reservation %s not found locally — treating as create", ha_id)
        process_reservation_created(payload)
        return

    mapped = map_reservation_to_model(res_data)
    if not mapped:
        return

    # Snapshot old values for signal detection
    old_status = existing.status
    old_check_in = existing.check_in_date
    old_check_out = existing.check_out_date

    # Protect WiseStay-owned fields on direct bookings
    is_wisestay_direct = (
        existing.channel == "direct" and existing.stripe_payment_intent_id
    )
    protected_fields = {
        "hostaway_reservation_id", "confirmation_code",
        "discount_amount", "points_earned", "points_redeemed",
        "stripe_payment_intent_id", "service_fee",
    }
    if is_wisestay_direct:
        protected_fields.update({
            "nightly_rate", "cleaning_fee", "total_amount", "taxes", "currency",
        })

    try:
        with transaction.atomic():
            for field, value in mapped.items():
                if field in protected_fields:
                    continue
                setattr(existing, field, value)
            existing.hostaway_raw_data = res_data
            existing.save()

        logger.info("Webhook: updated reservation %s", existing.confirmation_code)

        # Fire signals for significant changes
        if old_status != existing.status:
            if existing.status == "cancelled":
                reservation_cancelled.send(sender=Reservation, instance=existing)
            elif existing.status == "confirmed" and old_status == "pending":
                reservation_confirmed.send(
                    sender=Reservation, instance=existing, created=False,
                )

        if old_check_in != existing.check_in_date or old_check_out != existing.check_out_date:
            reservation_dates_changed.send(
                sender=Reservation,
                instance=existing,
                old_check_in=old_check_in,
                old_check_out=old_check_out,
            )
    except Exception:
        logger.exception("Webhook: failed to update reservation %s", ha_id)


def process_message_received(payload: dict):
    """
    Process a conversationMessageCreated webhook event.

    If the related reservation doesn't exist yet (out-of-order webhook),
    logs a warning and returns 200 (no retry needed).
    """
    msg_data = payload.get("data") or payload
    ha_reservation_id = str(msg_data.get("reservationId") or msg_data.get("reservation_id") or "")

    if not ha_reservation_id:
        logger.warning("Webhook message: no reservationId in payload — skipping")
        return

    reservation = Reservation.objects.filter(
        hostaway_reservation_id=ha_reservation_id
    ).first()
    if not reservation:
        logger.warning(
            "Webhook message: reservation %s not found (out-of-order webhook) — skipping",
            ha_reservation_id,
        )
        return

    if not reservation.guest_user:
        logger.info(
            "Webhook message: reservation %s has no guest_user — cannot create conversation",
            ha_reservation_id,
        )
        return

    body = msg_data.get("body") or msg_data.get("message") or msg_data.get("content") or ""
    if not body:
        logger.warning("Webhook message: empty body for reservation %s", ha_reservation_id)
        return

    # Get or create conversation
    conversation, _ = Conversation.objects.get_or_create(
        guest=reservation.guest_user,
        reservation=reservation,
        defaults={
            "channel": "whatsapp",
            "status": "active",
        },
    )

    Message.objects.create(
        conversation=conversation,
        sender_type="guest",
        content=body,
    )

    logger.info(
        "Webhook: created message in conversation %s for reservation %s",
        conversation.id, reservation.confirmation_code,
    )
