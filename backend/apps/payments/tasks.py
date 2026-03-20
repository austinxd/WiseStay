import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def generate_monthly_payouts_task(self):
    """Runs 1st of each month at 6:00 AM UTC. Generates payouts for previous month."""
    from .payout_service import PayoutService

    now = timezone.now()
    # Previous month
    first_of_month = now.replace(day=1)
    prev_month_last = first_of_month - timedelta(days=1)
    month = prev_month_last.month
    year = prev_month_last.year

    try:
        payouts = PayoutService.generate_monthly_payouts(month, year)
        logger.info("Generated %s payouts for %s/%s", len(payouts), month, year)
    except Exception as exc:
        logger.error("generate_monthly_payouts_task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def execute_payouts_task(self):
    """Runs 5th of each month at 10:00 AM UTC. Executes approved payouts."""
    from .payout_service import PayoutService

    try:
        result = PayoutService.execute_approved_payouts()
        logger.info(
            "Payouts executed: paid=%s, failed=%s, skipped=%s",
            result["paid"], result["failed"], result["skipped"],
        )
    except Exception as exc:
        logger.error("execute_payouts_task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def cancel_expired_pending_reservations(self):
    """Runs hourly. Cancels pending reservations older than 30 minutes."""
    from apps.reservations.models import Reservation

    cutoff = timezone.now() - timedelta(minutes=30)
    expired = Reservation.objects.filter(
        status="pending",
        channel="direct",
        created_at__lt=cutoff,
    )

    count = 0
    for reservation in expired:
        if reservation.stripe_payment_intent_id:
            try:
                from .stripe_service import StripeService

                StripeService.cancel_payment_intent(reservation.stripe_payment_intent_id)
            except Exception:
                pass

        reservation.status = "cancelled"
        reservation.cancelled_at = timezone.now()
        reservation.internal_notes = "Auto-cancelled: payment not completed within 30 minutes"
        reservation.save(update_fields=["status", "cancelled_at", "internal_notes", "updated_at"])
        count += 1

    if count:
        logger.info("Cancelled %s expired pending reservations", count)
