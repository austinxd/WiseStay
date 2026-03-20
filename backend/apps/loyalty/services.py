from __future__ import annotations

import logging
import math
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from apps.accounts.models import GuestProfile
from apps.reservations.models import Reservation

from .constants import EARN_RATE_DOLLARS_PER_POINT, POINT_VALUE_USD, POINTS_EXPIRY_MONTHS
from .models import PointTransaction, TierConfig, TierHistory

logger = logging.getLogger(__name__)

# Maximum combined discount (tier + points) as fraction of base_amount
MAX_DISCOUNT_FRACTION = Decimal("0.50")


class LoyaltyService:

    @staticmethod
    def earn_points(reservation_id: int) -> PointTransaction | None:
        reservation = Reservation.objects.select_related("guest_user").get(pk=reservation_id)

        if reservation.channel != "direct":
            return None
        if reservation.status != "checked_out":
            return None
        if reservation.guest_user is None:
            return None
        if reservation.points_earned > 0:
            return None  # idempotent

        base_amount = reservation.total_amount - reservation.discount_amount
        points = int(base_amount // EARN_RATE_DOLLARS_PER_POINT)
        if points <= 0:
            return None

        with transaction.atomic():
            profile = GuestProfile.objects.select_for_update().get(user=reservation.guest_user)
            new_balance = profile.points_balance + points

            pt = PointTransaction.objects.create(
                guest=reservation.guest_user,
                reservation=reservation,
                transaction_type="earn",
                points=points,
                expires_at=timezone.now() + timedelta(days=POINTS_EXPIRY_MONTHS * 30),
                points_remaining=points,
                balance_after=new_balance,
                description=f"Earned {points} pts from reservation {reservation.confirmation_code}",
            )

            profile.points_balance = new_balance
            profile.direct_bookings_count = F("direct_bookings_count") + 1
            profile.save(update_fields=["points_balance", "direct_bookings_count", "updated_at"])
            profile.refresh_from_db()

            reservation.points_earned = points
            reservation.save(update_fields=["points_earned", "updated_at"])

        # Recalculate tier outside the points transaction lock
        LoyaltyService.recalculate_tier(
            reservation.guest_user_id,
            triggered_by="reservation_completed",
        )

        logger.info(
            "Earned %s points for user %s on reservation %s",
            points, reservation.guest_user.email, reservation.confirmation_code,
        )
        return pt

    @staticmethod
    def redeem_points(
        guest_user_id: int,
        points_to_redeem: int,
        reservation_id: int | None = None,
    ) -> tuple[PointTransaction, Decimal]:
        if points_to_redeem <= 0:
            raise ValueError("Points to redeem must be positive")

        with transaction.atomic():
            profile = GuestProfile.objects.select_for_update().get(user_id=guest_user_id)

            if profile.points_balance < points_to_redeem:
                raise ValueError(
                    f"Insufficient points: balance={profile.points_balance}, "
                    f"requested={points_to_redeem}"
                )

            reservation = None
            if reservation_id:
                reservation = Reservation.objects.select_for_update().get(pk=reservation_id)
                if reservation.channel != "direct":
                    raise ValueError("Points can only be redeemed on direct bookings")
                if reservation.status != "pending":
                    raise ValueError(f"Reservation must be pending, got {reservation.status}")

            # FIFO: consume points from oldest earn transactions first
            earn_txs = (
                PointTransaction.objects
                .filter(
                    guest_id=guest_user_id,
                    transaction_type="earn",
                    points_remaining__gt=0,
                )
                .order_by("created_at")
                .select_for_update()
            )

            remaining_to_consume = points_to_redeem
            for earn_tx in earn_txs:
                if remaining_to_consume <= 0:
                    break
                consume = min(earn_tx.points_remaining, remaining_to_consume)
                earn_tx.points_remaining -= consume
                earn_tx.save(update_fields=["points_remaining", "updated_at"])
                remaining_to_consume -= consume

            if remaining_to_consume > 0:
                raise ValueError("Not enough redeemable points in FIFO queue")

            discount_amount = Decimal(str(points_to_redeem)) * Decimal(str(POINT_VALUE_USD))
            new_balance = profile.points_balance - points_to_redeem

            pt = PointTransaction.objects.create(
                guest_id=guest_user_id,
                reservation=reservation,
                transaction_type="redeem",
                points=-points_to_redeem,
                balance_after=new_balance,
                description=f"Redeemed {points_to_redeem} pts for ${discount_amount:.2f} discount",
            )

            profile.points_balance = new_balance
            profile.save(update_fields=["points_balance", "updated_at"])

            if reservation:
                reservation.points_redeemed = points_to_redeem
                reservation.discount_amount = (reservation.discount_amount or Decimal("0")) + discount_amount
                reservation.save(update_fields=["points_redeemed", "discount_amount", "updated_at"])

        logger.info("Redeemed %s points for user_id=%s", points_to_redeem, guest_user_id)
        return pt, discount_amount

    @staticmethod
    def expire_points() -> int:
        now = timezone.now()
        expired_txs = (
            PointTransaction.objects
            .filter(
                transaction_type="earn",
                points_remaining__gt=0,
                expires_at__lte=now,
            )
            .select_related("guest")
        )

        total_expired = 0
        guests_affected = set()

        # Group by guest to minimize locks
        guest_txs: dict[int, list] = {}
        for tx in expired_txs:
            guest_txs.setdefault(tx.guest_id, []).append(tx)

        for guest_id, txs in guest_txs.items():
            with transaction.atomic():
                profile = GuestProfile.objects.select_for_update().get(user_id=guest_id)
                guest_points_expired = 0

                for tx in txs:
                    # Re-fetch inside transaction to ensure consistency
                    tx.refresh_from_db()
                    if tx.points_remaining <= 0:
                        continue

                    pts = tx.points_remaining
                    tx.points_remaining = 0
                    tx.save(update_fields=["points_remaining", "updated_at"])

                    new_balance = profile.points_balance - pts
                    # Guard against negative balance (shouldn't happen but safety)
                    if new_balance < 0:
                        logger.warning(
                            "Points balance would go negative for user_id=%s (balance=%s, expiring=%s). Clamping to 0.",
                            guest_id, profile.points_balance, pts,
                        )
                        new_balance = 0

                    PointTransaction.objects.create(
                        guest_id=guest_id,
                        transaction_type="expire",
                        points=-pts,
                        balance_after=new_balance,
                        description=f"Expired {pts} pts (earned {tx.created_at.date()})",
                    )

                    profile.points_balance = new_balance
                    guest_points_expired += pts

                profile.save(update_fields=["points_balance", "updated_at"])
                total_expired += guest_points_expired
                guests_affected.add(guest_id)

        logger.info("Expired %s points for %s guests", total_expired, len(guests_affected))
        return total_expired

    @staticmethod
    def recalculate_tier(
        guest_user_id: int,
        triggered_by: str = "reservation_completed",
    ) -> str | None:
        profile = GuestProfile.objects.get(user_id=guest_user_id)
        old_tier = profile.loyalty_tier

        # Get all active tier configs, highest sort_order first
        tier_configs = TierConfig.objects.filter(is_active=True).order_by("-sort_order")
        new_tier = "bronze"  # default if nothing matches

        for tc in tier_configs:
            if (
                profile.direct_bookings_count >= tc.min_reservations
                and profile.successful_referrals_count >= tc.min_referrals
            ):
                new_tier = tc.tier_name
                break  # highest matching tier

        if new_tier == old_tier:
            return None

        # Determine if this is an upgrade (higher sort_order)
        old_sort = 0
        new_sort = 0
        for tc in tier_configs:
            if tc.tier_name == old_tier:
                old_sort = tc.sort_order
            if tc.tier_name == new_tier:
                new_sort = tc.sort_order

        with transaction.atomic():
            profile = GuestProfile.objects.select_for_update().get(user_id=guest_user_id)
            profile.loyalty_tier = new_tier
            profile.save(update_fields=["loyalty_tier", "updated_at"])

            direction = "upgraded" if new_sort > old_sort else "downgraded"
            TierHistory.objects.create(
                guest_id=guest_user_id,
                previous_tier=old_tier,
                new_tier=new_tier,
                reason=f"Tier {direction}: {old_tier} \u2192 {new_tier}",
                triggered_by=triggered_by,
            )

            # Award bonus points on upgrade
            if new_sort > old_sort:
                tier_config = TierConfig.objects.filter(tier_name=new_tier, is_active=True).first()
                if tier_config and tier_config.bonus_points_on_upgrade > 0:
                    bonus = tier_config.bonus_points_on_upgrade
                    profile.refresh_from_db()
                    new_balance = profile.points_balance + bonus

                    PointTransaction.objects.create(
                        guest_id=guest_user_id,
                        transaction_type="bonus",
                        points=bonus,
                        balance_after=new_balance,
                        description=f"Bonus for reaching {new_tier.title()} tier",
                    )

                    profile.points_balance = new_balance
                    profile.save(update_fields=["points_balance", "updated_at"])

        logger.info(
            "User %s tier changed: %s \u2192 %s (triggered_by=%s)",
            guest_user_id, old_tier, new_tier, triggered_by,
        )
        return new_tier

    @staticmethod
    def get_guest_loyalty_summary(guest_user_id: int) -> dict:
        profile = GuestProfile.objects.get(user_id=guest_user_id)

        tier_config = TierConfig.objects.filter(
            tier_name=profile.loyalty_tier, is_active=True
        ).first()

        tier_benefits = {}
        if tier_config:
            tier_benefits = {
                "discount_percent": float(tier_config.discount_percent),
                "early_checkin": tier_config.early_checkin,
                "late_checkout": tier_config.late_checkout,
                "priority_support": tier_config.priority_support,
            }

        # Points expiring soonest
        now = timezone.now()
        expiring_soon = (
            PointTransaction.objects
            .filter(
                guest_id=guest_user_id,
                transaction_type="earn",
                points_remaining__gt=0,
                expires_at__isnull=False,
                expires_at__gt=now,
            )
            .order_by("expires_at")
            .first()
        )
        points_expiring_soon = None
        if expiring_soon:
            points_expiring_soon = {
                "amount": expiring_soon.points_remaining,
                "expires_at": expiring_soon.expires_at.isoformat(),
            }

        # Next tier
        next_tier_info = None
        all_tiers = TierConfig.objects.filter(is_active=True).order_by("sort_order")
        current_sort = 0
        if tier_config:
            current_sort = tier_config.sort_order
        for tc in all_tiers:
            if tc.sort_order > current_sort:
                reservations_needed = max(0, tc.min_reservations - profile.direct_bookings_count)
                referrals_needed = max(0, tc.min_referrals - profile.successful_referrals_count)
                next_tier_info = {
                    "name": tc.tier_name,
                    "reservations_needed": reservations_needed,
                    "referrals_needed": referrals_needed,
                }
                break

        return {
            "tier": profile.loyalty_tier,
            "tier_benefits": tier_benefits,
            "points_balance": profile.points_balance,
            "points_expiring_soon": points_expiring_soon,
            "direct_bookings_count": profile.direct_bookings_count,
            "successful_referrals_count": profile.successful_referrals_count,
            "referral_code": profile.referral_code,
            "next_tier": next_tier_info,
        }

    @staticmethod
    def calculate_booking_discount(guest_user_id: int, base_amount: Decimal) -> dict:
        profile = GuestProfile.objects.get(user_id=guest_user_id)

        tier_config = TierConfig.objects.filter(
            tier_name=profile.loyalty_tier, is_active=True
        ).first()

        tier_discount_percent = Decimal("0")
        if tier_config:
            tier_discount_percent = tier_config.discount_percent

        tier_discount_amount = (base_amount * tier_discount_percent / Decimal("100")).quantize(Decimal("0.01"))

        # Floor: combined discount cannot exceed 50% of base
        max_total_discount = (base_amount * MAX_DISCOUNT_FRACTION).quantize(Decimal("0.01"))
        remaining_for_points = max_total_discount - tier_discount_amount
        if remaining_for_points < 0:
            remaining_for_points = Decimal("0")
            tier_discount_amount = max_total_discount

        point_value = Decimal(str(POINT_VALUE_USD))
        max_points_by_balance = profile.points_balance
        max_points_by_amount = int(remaining_for_points / point_value) if point_value > 0 else 0
        max_points_redeemable = min(max_points_by_balance, max_points_by_amount)
        max_points_discount = (Decimal(str(max_points_redeemable)) * point_value).quantize(Decimal("0.01"))

        min_total = base_amount - tier_discount_amount - max_points_discount

        return {
            "base_amount": float(base_amount),
            "tier_discount_percent": float(tier_discount_percent),
            "tier_discount_amount": float(tier_discount_amount),
            "max_points_redeemable": max_points_redeemable,
            "max_points_discount": float(max_points_discount),
            "min_total": float(min_total),
            "tier_name": profile.loyalty_tier,
        }
