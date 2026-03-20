from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import GuestProfile, User
from apps.loyalty.constants import EARN_RATE_DOLLARS_PER_POINT, REFERRAL_BONUS_POINTS
from apps.loyalty.models import PointTransaction, TierConfig, TierHistory
from apps.loyalty.services import LoyaltyService
from apps.properties.models import Property
from apps.reservations.models import Reservation


def _create_owner():
    return User.objects.create_user(
        username="owner", email="owner@test.com", password="test", role="owner",
    )


def _create_guest(username="guest1", email="guest@test.com"):
    return User.objects.create_user(
        username=username, email=email, password="test", role="guest",
    )


def _create_property(owner):
    return Property.objects.create(
        owner=owner, name="Test Villa", slug=f"test-villa-{owner.pk}",
        property_type="villa", address="123 St", city="Miami", state="FL",
        zip_code="33101", base_nightly_rate=Decimal("200.00"),
    )


def _create_reservation(prop, guest, **kwargs):
    defaults = {
        "property": prop,
        "guest_user": guest,
        "channel": "direct",
        "status": "checked_out",
        "confirmation_code": f"WS-{Reservation.objects.count() + 1:06d}",
        "check_in_date": date(2025, 7, 1),
        "check_out_date": date(2025, 7, 5),
        "nights": 4,
        "guest_name": "Test Guest",
        "nightly_rate": Decimal("200.00"),
        "total_amount": Decimal("800.00"),
    }
    defaults.update(kwargs)
    return Reservation.objects.create(**defaults)


def _seed_tiers():
    TierConfig.objects.all().delete()
    TierConfig.objects.create(tier_name="bronze", min_reservations=0, min_referrals=0, discount_percent=0, sort_order=1, bonus_points_on_upgrade=0)
    TierConfig.objects.create(tier_name="silver", min_reservations=3, min_referrals=1, discount_percent=5, sort_order=2, bonus_points_on_upgrade=25)
    TierConfig.objects.create(tier_name="gold", min_reservations=8, min_referrals=3, discount_percent=10, sort_order=3, bonus_points_on_upgrade=50, early_checkin=True, late_checkout=True, priority_support=True)
    TierConfig.objects.create(tier_name="platinum", min_reservations=15, min_referrals=5, discount_percent=15, sort_order=4, bonus_points_on_upgrade=100, early_checkin=True, late_checkout=True, priority_support=True)


class TestEarnPoints(TestCase):
    def setUp(self):
        _seed_tiers()
        self.owner = _create_owner()
        self.guest = _create_guest()
        self.prop = _create_property(self.owner)

    def test_earns_correct_points(self):
        res = _create_reservation(self.prop, self.guest, total_amount=Decimal("450.00"))
        pt = LoyaltyService.earn_points(res.id)

        self.assertIsNotNone(pt)
        self.assertEqual(pt.points, 22)  # floor(450/20)
        self.assertEqual(pt.transaction_type, "earn")
        self.assertEqual(pt.points_remaining, 22)
        self.assertIsNotNone(pt.expires_at)

    def test_earns_with_discount_excluded(self):
        res = _create_reservation(
            self.prop, self.guest,
            total_amount=Decimal("500.00"),
            discount_amount=Decimal("50.00"),
        )
        pt = LoyaltyService.earn_points(res.id)

        # (500-50)/20 = 22.5 → floor = 22
        self.assertEqual(pt.points, 22)

    def test_updates_profile_balance(self):
        res = _create_reservation(self.prop, self.guest, total_amount=Decimal("400.00"))
        LoyaltyService.earn_points(res.id)

        profile = GuestProfile.objects.get(user=self.guest)
        self.assertEqual(profile.points_balance, 20)  # 400/20
        self.assertEqual(profile.direct_bookings_count, 1)

    def test_updates_reservation_points_earned(self):
        res = _create_reservation(self.prop, self.guest, total_amount=Decimal("400.00"))
        LoyaltyService.earn_points(res.id)

        res.refresh_from_db()
        self.assertEqual(res.points_earned, 20)

    def test_idempotent_double_call(self):
        res = _create_reservation(self.prop, self.guest, total_amount=Decimal("400.00"))
        pt1 = LoyaltyService.earn_points(res.id)
        pt2 = LoyaltyService.earn_points(res.id)

        self.assertIsNotNone(pt1)
        self.assertIsNone(pt2)
        self.assertEqual(PointTransaction.objects.filter(guest=self.guest).count(), 1)

    def test_skips_non_direct_channel(self):
        res = _create_reservation(self.prop, self.guest, channel="airbnb")
        self.assertIsNone(LoyaltyService.earn_points(res.id))

    def test_skips_non_checkout_status(self):
        res = _create_reservation(self.prop, self.guest, status="confirmed")
        self.assertIsNone(LoyaltyService.earn_points(res.id))

    def test_skips_no_guest_user(self):
        res = _create_reservation(self.prop, self.guest, guest_user=None)
        self.assertIsNone(LoyaltyService.earn_points(res.id))

    def test_skips_very_small_amount(self):
        res = _create_reservation(self.prop, self.guest, total_amount=Decimal("15.00"))
        self.assertIsNone(LoyaltyService.earn_points(res.id))


class TestRedeemPoints(TestCase):
    def setUp(self):
        _seed_tiers()
        self.owner = _create_owner()
        self.guest = _create_guest()
        self.prop = _create_property(self.owner)
        self._give_points(100)

    def _give_points(self, points, days_ago=0):
        """Helper to give points by creating earn transactions."""
        profile = GuestProfile.objects.get(user=self.guest)
        created = timezone.now() - timedelta(days=days_ago)
        pt = PointTransaction.objects.create(
            guest=self.guest,
            transaction_type="earn",
            points=points,
            points_remaining=points,
            balance_after=profile.points_balance + points,
            expires_at=created + timedelta(days=365),
            description="Test earn",
        )
        profile.points_balance += points
        profile.save(update_fields=["points_balance"])
        return pt

    def test_redeems_and_returns_discount(self):
        pt, discount = LoyaltyService.redeem_points(self.guest.id, 30)

        self.assertEqual(pt.points, -30)
        self.assertEqual(pt.transaction_type, "redeem")
        self.assertEqual(discount, Decimal("30.00"))

    def test_updates_profile_balance(self):
        LoyaltyService.redeem_points(self.guest.id, 30)

        profile = GuestProfile.objects.get(user=self.guest)
        self.assertEqual(profile.points_balance, 70)

    def test_fifo_consumes_oldest_first(self):
        # Already have 100 pts from setUp. Add 50 more (newer).
        self._give_points(50)

        # Redeem 120 — should consume all 100 from first, 20 from second
        LoyaltyService.redeem_points(self.guest.id, 120)

        earn_txs = PointTransaction.objects.filter(
            guest=self.guest, transaction_type="earn",
        ).order_by("created_at")

        self.assertEqual(earn_txs[0].points_remaining, 0)   # fully consumed
        self.assertEqual(earn_txs[1].points_remaining, 30)  # 50 - 20

    def test_fifo_three_transactions(self):
        """Test FIFO with 3 earn transactions of different amounts."""
        self._give_points(40)   # +40 = 140
        self._give_points(60)   # +60 = 200

        # Redeem 130: should consume 100 + 30 from the 40-pt tx
        LoyaltyService.redeem_points(self.guest.id, 130)

        earn_txs = PointTransaction.objects.filter(
            guest=self.guest, transaction_type="earn",
        ).order_by("created_at")

        self.assertEqual(earn_txs[0].points_remaining, 0)    # 100 → 0
        self.assertEqual(earn_txs[1].points_remaining, 10)   # 40 → 10
        self.assertEqual(earn_txs[2].points_remaining, 60)   # untouched

    def test_updates_reservation_on_redeem(self):
        res = _create_reservation(
            self.prop, self.guest,
            status="pending",
            total_amount=Decimal("500.00"),
        )
        LoyaltyService.redeem_points(self.guest.id, 50, reservation_id=res.id)

        res.refresh_from_db()
        self.assertEqual(res.points_redeemed, 50)
        self.assertEqual(res.discount_amount, Decimal("50.00"))

    def test_rejects_insufficient_points(self):
        with self.assertRaises(ValueError) as ctx:
            LoyaltyService.redeem_points(self.guest.id, 200)
        self.assertIn("Insufficient", str(ctx.exception))

    def test_rejects_zero_points(self):
        with self.assertRaises(ValueError):
            LoyaltyService.redeem_points(self.guest.id, 0)

    def test_rejects_non_direct_reservation(self):
        res = _create_reservation(self.prop, self.guest, channel="airbnb", status="pending")
        with self.assertRaises(ValueError) as ctx:
            LoyaltyService.redeem_points(self.guest.id, 10, reservation_id=res.id)
        self.assertIn("direct", str(ctx.exception))

    def test_rejects_non_pending_reservation(self):
        res = _create_reservation(self.prop, self.guest, status="confirmed")
        with self.assertRaises(ValueError) as ctx:
            LoyaltyService.redeem_points(self.guest.id, 10, reservation_id=res.id)
        self.assertIn("pending", str(ctx.exception))


class TestExpirePoints(TestCase):
    def setUp(self):
        self.guest = _create_guest()

    def _earn(self, points, expires_in_days):
        profile = GuestProfile.objects.get(user=self.guest)
        pt = PointTransaction.objects.create(
            guest=self.guest,
            transaction_type="earn",
            points=points,
            points_remaining=points,
            balance_after=profile.points_balance + points,
            expires_at=timezone.now() + timedelta(days=expires_in_days),
            description="Test earn",
        )
        profile.points_balance += points
        profile.save(update_fields=["points_balance"])
        return pt

    def test_expires_old_points(self):
        self._earn(50, expires_in_days=-1)  # already expired
        self._earn(30, expires_in_days=30)  # still valid

        total = LoyaltyService.expire_points()

        self.assertEqual(total, 50)
        profile = GuestProfile.objects.get(user=self.guest)
        self.assertEqual(profile.points_balance, 30)

    def test_creates_expire_transaction(self):
        self._earn(50, expires_in_days=-1)
        LoyaltyService.expire_points()

        expire_tx = PointTransaction.objects.filter(
            guest=self.guest, transaction_type="expire",
        ).first()
        self.assertIsNotNone(expire_tx)
        self.assertEqual(expire_tx.points, -50)

    def test_sets_points_remaining_to_zero(self):
        earn_tx = self._earn(50, expires_in_days=-1)
        LoyaltyService.expire_points()

        earn_tx.refresh_from_db()
        self.assertEqual(earn_tx.points_remaining, 0)

    def test_no_double_expire(self):
        self._earn(50, expires_in_days=-1)
        LoyaltyService.expire_points()
        total2 = LoyaltyService.expire_points()

        self.assertEqual(total2, 0)

    def test_partial_remaining(self):
        """If some points from an earn tx were already redeemed, only expire the remainder."""
        earn_tx = self._earn(50, expires_in_days=-1)
        earn_tx.points_remaining = 20  # 30 were already redeemed
        earn_tx.save()

        total = LoyaltyService.expire_points()
        self.assertEqual(total, 20)


class TestRecalculateTier(TestCase):
    def setUp(self):
        _seed_tiers()
        self.guest = _create_guest()

    def test_stays_bronze_by_default(self):
        result = LoyaltyService.recalculate_tier(self.guest.id)
        self.assertIsNone(result)  # no change

    def test_upgrades_to_silver(self):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.direct_bookings_count = 3
        profile.successful_referrals_count = 1
        profile.save()

        new_tier = LoyaltyService.recalculate_tier(self.guest.id)
        self.assertEqual(new_tier, "silver")

        profile.refresh_from_db()
        self.assertEqual(profile.loyalty_tier, "silver")

    def test_upgrades_to_gold(self):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.direct_bookings_count = 10
        profile.successful_referrals_count = 5
        profile.save()

        new_tier = LoyaltyService.recalculate_tier(self.guest.id)
        self.assertEqual(new_tier, "gold")

    def test_upgrades_to_platinum(self):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.direct_bookings_count = 20
        profile.successful_referrals_count = 5
        profile.save()

        new_tier = LoyaltyService.recalculate_tier(self.guest.id)
        self.assertEqual(new_tier, "platinum")

    def test_requires_both_conditions(self):
        """Lots of bookings but no referrals should only reach bronze (needs >=1 for silver)."""
        profile = GuestProfile.objects.get(user=self.guest)
        profile.direct_bookings_count = 20
        profile.successful_referrals_count = 0
        profile.save()

        result = LoyaltyService.recalculate_tier(self.guest.id)
        self.assertIsNone(result)  # stays bronze

    def test_creates_tier_history(self):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.direct_bookings_count = 3
        profile.successful_referrals_count = 1
        profile.save()

        LoyaltyService.recalculate_tier(self.guest.id)

        history = TierHistory.objects.get(guest=self.guest)
        self.assertEqual(history.previous_tier, "bronze")
        self.assertEqual(history.new_tier, "silver")

    def test_awards_bonus_on_upgrade(self):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.direct_bookings_count = 3
        profile.successful_referrals_count = 1
        profile.save()

        LoyaltyService.recalculate_tier(self.guest.id)

        bonus_tx = PointTransaction.objects.filter(
            guest=self.guest, transaction_type="bonus",
        ).first()
        self.assertIsNotNone(bonus_tx)
        self.assertEqual(bonus_tx.points, 25)  # silver bonus

        profile.refresh_from_db()
        self.assertEqual(profile.points_balance, 25)

    def test_no_change_returns_none(self):
        result = LoyaltyService.recalculate_tier(self.guest.id)
        self.assertIsNone(result)
        self.assertFalse(TierHistory.objects.filter(guest=self.guest).exists())

    def test_respects_custom_tier_config(self):
        """If admin changes thresholds, recalculate uses new values."""
        TierConfig.objects.filter(tier_name="silver").update(min_reservations=1, min_referrals=0)

        profile = GuestProfile.objects.get(user=self.guest)
        profile.direct_bookings_count = 1
        profile.save()

        new_tier = LoyaltyService.recalculate_tier(self.guest.id)
        self.assertEqual(new_tier, "silver")


class TestCalculateBookingDiscount(TestCase):
    def setUp(self):
        _seed_tiers()
        self.guest = _create_guest()

    def _set_tier_and_points(self, tier, points):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.loyalty_tier = tier
        profile.points_balance = points
        profile.save()

    def test_bronze_no_discount(self):
        self._set_tier_and_points("bronze", 0)
        result = LoyaltyService.calculate_booking_discount(self.guest.id, Decimal("500"))

        self.assertEqual(result["tier_discount_percent"], 0)
        self.assertEqual(result["tier_discount_amount"], 0)
        self.assertEqual(result["max_points_redeemable"], 0)

    def test_gold_tier_discount(self):
        self._set_tier_and_points("gold", 0)
        result = LoyaltyService.calculate_booking_discount(self.guest.id, Decimal("800"))

        self.assertEqual(result["tier_discount_percent"], 10)
        self.assertEqual(result["tier_discount_amount"], 80.00)

    def test_points_discount(self):
        self._set_tier_and_points("bronze", 200)
        result = LoyaltyService.calculate_booking_discount(self.guest.id, Decimal("500"))

        self.assertEqual(result["max_points_redeemable"], 200)
        self.assertEqual(result["max_points_discount"], 200.00)

    def test_50_percent_floor(self):
        """Combined discount cannot exceed 50% of base_amount."""
        self._set_tier_and_points("gold", 500)
        result = LoyaltyService.calculate_booking_discount(self.guest.id, Decimal("800"))

        # Gold = 10% = $80 tier discount
        # 50% of 800 = $400 max total discount
        # Points can contribute $400 - $80 = $320 → 320 points
        self.assertEqual(result["tier_discount_amount"], 80.00)
        self.assertEqual(result["max_points_redeemable"], 320)
        self.assertEqual(result["max_points_discount"], 320.00)
        self.assertEqual(result["min_total"], 400.00)

    def test_limited_by_balance(self):
        self._set_tier_and_points("bronze", 30)
        result = LoyaltyService.calculate_booking_discount(self.guest.id, Decimal("500"))

        self.assertEqual(result["max_points_redeemable"], 30)
        self.assertEqual(result["max_points_discount"], 30.00)


class TestGetGuestLoyaltySummary(TestCase):
    def setUp(self):
        _seed_tiers()
        self.guest = _create_guest()

    def test_returns_complete_summary(self):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.loyalty_tier = "silver"
        profile.points_balance = 100
        profile.direct_bookings_count = 5
        profile.successful_referrals_count = 2
        profile.save()

        summary = LoyaltyService.get_guest_loyalty_summary(self.guest.id)

        self.assertEqual(summary["tier"], "silver")
        self.assertEqual(summary["points_balance"], 100)
        self.assertEqual(summary["direct_bookings_count"], 5)
        self.assertEqual(summary["referral_code"], profile.referral_code)
        self.assertIsNotNone(summary["next_tier"])
        self.assertEqual(summary["next_tier"]["name"], "gold")
        self.assertEqual(summary["next_tier"]["reservations_needed"], 3)  # 8-5
        self.assertEqual(summary["next_tier"]["referrals_needed"], 1)    # 3-2

    def test_platinum_has_no_next_tier(self):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.loyalty_tier = "platinum"
        profile.save()

        summary = LoyaltyService.get_guest_loyalty_summary(self.guest.id)
        self.assertIsNone(summary["next_tier"])

    def test_includes_tier_benefits(self):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.loyalty_tier = "gold"
        profile.save()

        summary = LoyaltyService.get_guest_loyalty_summary(self.guest.id)
        benefits = summary["tier_benefits"]
        self.assertEqual(benefits["discount_percent"], 10)
        self.assertTrue(benefits["early_checkin"])
        self.assertTrue(benefits["late_checkout"])
        self.assertTrue(benefits["priority_support"])
