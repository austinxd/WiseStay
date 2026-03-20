import logging

from django.db import transaction
from django.db.models import F

from apps.accounts.models import GuestProfile
from apps.reservations.models import Reservation

from .models import PointTransaction

logger = logging.getLogger(__name__)


def on_reservation_checked_out(sender, instance, **kwargs):
    """
    Listener for reservation checkout — triggers loyalty point earning
    and referral completion asynchronously via Celery.

    Idempotent: the Celery task checks points_earned == 0 before proceeding.
    """
    reservation = instance
    if reservation.channel != "direct":
        return
    if reservation.status != "checked_out":
        return
    if reservation.guest_user is None:
        return

    from .tasks import process_checkout_loyalty

    process_checkout_loyalty.delay(reservation.id)
    logger.info(
        "Dispatched checkout loyalty processing for reservation %s",
        reservation.confirmation_code,
    )


def on_reservation_cancelled(sender, instance, **kwargs):
    """
    Listener for reservation cancellation — refunds redeemed points
    and reverts earned points if applicable.
    """
    reservation = instance
    if reservation.channel != "direct":
        return
    if reservation.guest_user is None:
        return

    guest_user_id = reservation.guest_user_id

    with transaction.atomic():
        profile = GuestProfile.objects.select_for_update().get(user_id=guest_user_id)

        # 1. Refund redeemed points
        if reservation.points_redeemed > 0:
            refund_pts = reservation.points_redeemed
            new_balance = profile.points_balance + refund_pts

            PointTransaction.objects.create(
                guest_id=guest_user_id,
                reservation=reservation,
                transaction_type="adjust",
                points=refund_pts,
                balance_after=new_balance,
                description=(
                    f"Points refunded — reservation "
                    f"{reservation.confirmation_code} cancelled"
                ),
            )

            profile.points_balance = new_balance
            reservation.points_redeemed = 0
            reservation.discount_amount = 0
            reservation.save(update_fields=[
                "points_redeemed", "discount_amount", "updated_at",
            ])

            logger.info(
                "Refunded %s points for user %s (reservation %s cancelled)",
                refund_pts, guest_user_id, reservation.confirmation_code,
            )

        # 2. Revert earned points (if checkout already happened before cancel)
        if reservation.points_earned > 0:
            earned_pts = reservation.points_earned
            new_balance = profile.points_balance - earned_pts

            if new_balance < 0:
                logger.warning(
                    "Balance would go negative for user %s (balance=%s, "
                    "reverting=%s). Clamping to 0 — manual review needed.",
                    guest_user_id, profile.points_balance, earned_pts,
                )
                new_balance = 0

            PointTransaction.objects.create(
                guest_id=guest_user_id,
                reservation=reservation,
                transaction_type="adjust",
                points=-earned_pts,
                balance_after=new_balance,
                description=(
                    f"Points reversed — reservation "
                    f"{reservation.confirmation_code} cancelled after checkout"
                ),
            )

            profile.points_balance = new_balance

            if profile.direct_bookings_count > 0:
                profile.direct_bookings_count = F("direct_bookings_count") - 1

            reservation.points_earned = 0
            reservation.save(update_fields=["points_earned", "updated_at"])

            logger.info(
                "Reversed %s earned points for user %s (reservation %s)",
                earned_pts, guest_user_id, reservation.confirmation_code,
            )

        profile.save(update_fields=[
            "points_balance", "direct_bookings_count", "updated_at",
        ])

    # Recalculate tier if points were reversed (bookings count changed)
    if reservation.points_earned == 0 and instance.points_earned != 0:
        from .services import LoyaltyService

        LoyaltyService.recalculate_tier(
            guest_user_id, triggered_by="admin_adjustment",
        )
