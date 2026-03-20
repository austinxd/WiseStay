import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import GuestProfile, User

from .constants import REFERRAL_BONUS_POINTS, REFERRAL_EXPIRY_DAYS
from .models import PointTransaction, Referral

logger = logging.getLogger(__name__)


class ReferralService:

    @staticmethod
    def create_referral(referrer_code: str, referred_user_id: int) -> Referral:
        # Find the referrer by code
        try:
            referrer_profile = GuestProfile.objects.select_related("user").get(
                referral_code=referrer_code
            )
        except GuestProfile.DoesNotExist:
            raise ValueError(f"Invalid referral code: {referrer_code}")

        referrer = referrer_profile.user

        if not referrer.is_active or referrer.role != "guest":
            raise ValueError("Referrer account is not active")

        if referrer.id == referred_user_id:
            raise ValueError("You cannot refer yourself")

        # Check if referred user already has a referral (OneToOne enforces this at DB level too)
        if Referral.objects.filter(referred_user_id=referred_user_id).exists():
            raise ValueError("This user has already been referred")

        referred_user = User.objects.get(pk=referred_user_id)
        if referred_user.role != "guest":
            raise ValueError("Referred user must be a guest")

        referral = Referral.objects.create(
            referrer=referrer,
            referred_user=referred_user,
            referral_code_used=referrer_code,
            status="pending",
        )

        logger.info(
            "Referral created: %s referred %s (code=%s)",
            referrer.email, referred_user.email, referrer_code,
        )
        return referral

    @staticmethod
    def complete_referral(referred_user_id: int, reservation_id: int) -> Referral | None:
        from apps.reservations.models import Reservation

        try:
            referral = Referral.objects.select_related(
                "referrer", "referred_user"
            ).get(
                referred_user_id=referred_user_id,
                status="pending",
            )
        except Referral.DoesNotExist:
            return None

        reservation = Reservation.objects.get(pk=reservation_id)
        if reservation.channel != "direct" or reservation.status != "checked_out":
            return None

        with transaction.atomic():
            referral.status = "completed"
            referral.completed_at = timezone.now()
            referral.referred_reservation = reservation
            referral.reward_points_granted = REFERRAL_BONUS_POINTS
            referral.save(update_fields=[
                "status", "completed_at", "referred_reservation",
                "reward_points_granted", "updated_at",
            ])

            # Award bonus points to the referrer
            referrer_profile = GuestProfile.objects.select_for_update().get(
                user=referral.referrer
            )
            referrer_profile.successful_referrals_count += 1
            new_balance = referrer_profile.points_balance + REFERRAL_BONUS_POINTS
            referrer_profile.points_balance = new_balance
            referrer_profile.save(update_fields=[
                "successful_referrals_count", "points_balance", "updated_at",
            ])

            PointTransaction.objects.create(
                guest=referral.referrer,
                reservation=reservation,
                transaction_type="referral_bonus",
                points=REFERRAL_BONUS_POINTS,
                balance_after=new_balance,
                description=f"Referral bonus: {referral.referred_user.email} completed first booking",
            )

        # Recalculate referrer tier (may upgrade due to new referral count)
        from .services import LoyaltyService
        LoyaltyService.recalculate_tier(
            referral.referrer_id,
            triggered_by="referral_completed",
        )

        logger.info(
            "Referral completed: %s referred %s (bonus=%s pts)",
            referral.referrer.email, referral.referred_user.email,
            REFERRAL_BONUS_POINTS,
        )
        return referral

    @staticmethod
    def expire_stale_referrals() -> int:
        cutoff = timezone.now() - timedelta(days=REFERRAL_EXPIRY_DAYS)
        stale = Referral.objects.filter(
            status="pending",
            created_at__lt=cutoff,
        )
        count = stale.update(status="expired")
        if count:
            logger.info("Expired %s stale referrals", count)
        return count

    @staticmethod
    def get_referral_stats(guest_user_id: int) -> dict:
        profile = GuestProfile.objects.get(user_id=guest_user_id)
        referrals = Referral.objects.filter(
            referrer_id=guest_user_id
        ).select_related("referred_user").order_by("-created_at")

        total = referrals.count()
        completed = referrals.filter(status="completed").count()
        pending = referrals.filter(status="pending").count()
        expired = referrals.filter(status="expired").count()

        total_bonus = referrals.filter(status="completed").aggregate(
            total=Sum("reward_points_granted")
        )["total"] or 0

        recent = []
        for ref in referrals[:10]:
            name = ref.referred_user.get_full_name() or ref.referred_user.email
            # Mask name for privacy: "John D." or just first few chars of email
            if " " in name:
                parts = name.split()
                display_name = f"{parts[0]} {parts[-1][0]}."
            else:
                display_name = f"{name[:3]}***"

            recent.append({
                "name": display_name,
                "status": ref.status,
                "date": ref.created_at.date().isoformat(),
                "points_earned": ref.reward_points_granted,
            })

        return {
            "referral_code": profile.referral_code,
            "total_referred": total,
            "completed": completed,
            "pending": pending,
            "expired": expired,
            "total_bonus_points_earned": total_bonus,
            "recent_referrals": recent,
        }
