import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def expire_points_daily(self):
    """Expire stale points. Runs daily at 2:00 AM UTC."""
    from .services import LoyaltyService

    try:
        total = LoyaltyService.expire_points()
        logger.info("expire_points_daily: expired %s points", total)
    except Exception as exc:
        logger.error("expire_points_daily failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def expire_stale_referrals_daily(self):
    """Expire pending referrals past the deadline. Runs daily at 2:30 AM UTC."""
    from .referral_service import ReferralService

    try:
        count = ReferralService.expire_stale_referrals()
        logger.info("expire_stale_referrals_daily: expired %s referrals", count)
    except Exception as exc:
        logger.error("expire_stale_referrals_daily failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def process_checkout_loyalty(self, reservation_id: int):
    """
    Process loyalty after a direct reservation checkout.
    Called async from the signal handler to avoid blocking checkout flow.
    """
    from .referral_service import ReferralService
    from .services import LoyaltyService

    try:
        pt = LoyaltyService.earn_points(reservation_id)
        if pt:
            logger.info(
                "Earned %s points for reservation %s",
                pt.points, reservation_id,
            )

        from apps.reservations.models import Reservation

        reservation = Reservation.objects.get(pk=reservation_id)
        if reservation.guest_user_id:
            referral = ReferralService.complete_referral(
                reservation.guest_user_id, reservation_id,
            )
            if referral:
                logger.info(
                    "Referral completed for user %s on reservation %s",
                    reservation.guest_user_id, reservation_id,
                )
    except Exception as exc:
        logger.error(
            "process_checkout_loyalty failed for reservation %s: %s",
            reservation_id, exc, exc_info=True,
        )
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=1, default_retry_delay=60)
def recalculate_all_tiers(self):
    """
    Recalculate tiers for all active guests.
    Triggered manually from Django Admin after changing TierConfig thresholds.
    """
    from apps.accounts.models import GuestProfile

    from .services import LoyaltyService

    profiles = GuestProfile.objects.filter(user__is_active=True).values_list(
        "user_id", flat=True,
    )
    changed = 0
    for user_id in profiles:
        try:
            result = LoyaltyService.recalculate_tier(
                user_id, triggered_by="admin_adjustment",
            )
            if result:
                changed += 1
        except Exception:
            logger.error("Failed to recalculate tier for user %s", user_id, exc_info=True)

    logger.info("recalculate_all_tiers: %s/%s tiers changed", changed, len(profiles))
