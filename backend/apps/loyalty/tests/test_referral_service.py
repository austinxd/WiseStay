from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import GuestProfile, User
from apps.loyalty.constants import REFERRAL_BONUS_POINTS
from apps.loyalty.models import PointTransaction, Referral, TierConfig, TierHistory
from apps.loyalty.referral_service import ReferralService
from apps.properties.models import Property
from apps.reservations.models import Reservation


def _create_guest(username, email):
    return User.objects.create_user(
        username=username, email=email, password="test", role="guest",
    )


def _seed_tiers():
    TierConfig.objects.all().delete()
    TierConfig.objects.create(tier_name="bronze", min_reservations=0, min_referrals=0, discount_percent=0, sort_order=1)
    TierConfig.objects.create(tier_name="silver", min_reservations=3, min_referrals=1, discount_percent=5, sort_order=2, bonus_points_on_upgrade=25)


class TestCreateReferral(TestCase):
    def setUp(self):
        self.referrer = _create_guest("referrer", "referrer@test.com")
        self.referred = _create_guest("referred", "referred@test.com")
        self.referrer_profile = GuestProfile.objects.get(user=self.referrer)

    def test_creates_pending_referral(self):
        ref = ReferralService.create_referral(
            self.referrer_profile.referral_code,
            self.referred.id,
        )
        self.assertEqual(ref.status, "pending")
        self.assertEqual(ref.referrer_id, self.referrer.id)
        self.assertEqual(ref.referred_user_id, self.referred.id)
        self.assertEqual(ref.referral_code_used, self.referrer_profile.referral_code)

    def test_rejects_invalid_code(self):
        with self.assertRaises(ValueError) as ctx:
            ReferralService.create_referral("WS-FAKE", self.referred.id)
        self.assertIn("Invalid", str(ctx.exception))

    def test_rejects_self_referral(self):
        with self.assertRaises(ValueError) as ctx:
            ReferralService.create_referral(
                self.referrer_profile.referral_code,
                self.referrer.id,
            )
        self.assertIn("yourself", str(ctx.exception))

    def test_rejects_duplicate_referred_user(self):
        ReferralService.create_referral(
            self.referrer_profile.referral_code,
            self.referred.id,
        )
        another_referrer = _create_guest("ref2", "ref2@test.com")
        another_profile = GuestProfile.objects.get(user=another_referrer)

        with self.assertRaises(ValueError) as ctx:
            ReferralService.create_referral(
                another_profile.referral_code,
                self.referred.id,
            )
        self.assertIn("already been referred", str(ctx.exception))


class TestCompleteReferral(TestCase):
    def setUp(self):
        _seed_tiers()
        self.referrer = _create_guest("referrer", "referrer@test.com")
        self.referred = _create_guest("referred", "referred@test.com")
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="test", role="owner",
        )
        self.prop = Property.objects.create(
            owner=self.owner, name="Villa", slug="villa",
            property_type="villa", address="123 St", city="Miami",
            state="FL", zip_code="33101", base_nightly_rate=Decimal("200.00"),
        )

        referrer_profile = GuestProfile.objects.get(user=self.referrer)
        self.referral = Referral.objects.create(
            referrer=self.referrer,
            referred_user=self.referred,
            referral_code_used=referrer_profile.referral_code,
            status="pending",
        )

    def _create_reservation(self, guest):
        return Reservation.objects.create(
            property=self.prop, guest_user=guest,
            channel="direct", status="checked_out",
            confirmation_code=f"WS-{Reservation.objects.count() + 1:06d}",
            check_in_date=date(2025, 7, 1), check_out_date=date(2025, 7, 5),
            nights=4, guest_name="Test", nightly_rate=Decimal("200.00"),
            total_amount=Decimal("800.00"),
        )

    def test_completes_referral(self):
        res = self._create_reservation(self.referred)
        result = ReferralService.complete_referral(self.referred.id, res.id)

        self.assertIsNotNone(result)
        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(result.completed_at)
        self.assertEqual(result.reward_points_granted, REFERRAL_BONUS_POINTS)
        self.assertEqual(result.referred_reservation_id, res.id)

    def test_awards_bonus_to_referrer(self):
        res = self._create_reservation(self.referred)
        ReferralService.complete_referral(self.referred.id, res.id)

        profile = GuestProfile.objects.get(user=self.referrer)
        self.assertEqual(profile.points_balance, REFERRAL_BONUS_POINTS)
        self.assertEqual(profile.successful_referrals_count, 1)

        bonus_tx = PointTransaction.objects.filter(
            guest=self.referrer, transaction_type="referral_bonus",
        ).first()
        self.assertIsNotNone(bonus_tx)
        self.assertEqual(bonus_tx.points, REFERRAL_BONUS_POINTS)

    def test_returns_none_if_no_pending_referral(self):
        other = _create_guest("other", "other@test.com")
        res = self._create_reservation(other)
        result = ReferralService.complete_referral(other.id, res.id)
        self.assertIsNone(result)

    def test_returns_none_for_non_direct_reservation(self):
        res = self._create_reservation(self.referred)
        res.channel = "airbnb"
        res.save()

        result = ReferralService.complete_referral(self.referred.id, res.id)
        self.assertIsNone(result)

    def test_recalculates_referrer_tier(self):
        """Completing a referral should trigger tier recalculation for the referrer."""
        referrer_profile = GuestProfile.objects.get(user=self.referrer)
        referrer_profile.direct_bookings_count = 3
        referrer_profile.save()

        res = self._create_reservation(self.referred)
        ReferralService.complete_referral(self.referred.id, res.id)

        referrer_profile.refresh_from_db()
        # 3 bookings + 1 referral meets silver (3 res, 1 ref)
        self.assertEqual(referrer_profile.loyalty_tier, "silver")


class TestExpireStaleReferrals(TestCase):
    def setUp(self):
        self.referrer = _create_guest("referrer", "referrer@test.com")
        self.referred = _create_guest("referred", "referred@test.com")
        referrer_profile = GuestProfile.objects.get(user=self.referrer)

        self.referral = Referral.objects.create(
            referrer=self.referrer,
            referred_user=self.referred,
            referral_code_used=referrer_profile.referral_code,
            status="pending",
        )

    def test_expires_old_referrals(self):
        # Make the referral older than 90 days
        Referral.objects.filter(pk=self.referral.pk).update(
            created_at=timezone.now() - timedelta(days=91)
        )

        count = ReferralService.expire_stale_referrals()
        self.assertEqual(count, 1)

        self.referral.refresh_from_db()
        self.assertEqual(self.referral.status, "expired")

    def test_does_not_expire_recent(self):
        count = ReferralService.expire_stale_referrals()
        self.assertEqual(count, 0)

        self.referral.refresh_from_db()
        self.assertEqual(self.referral.status, "pending")


class TestGetReferralStats(TestCase):
    def setUp(self):
        self.referrer = _create_guest("referrer", "referrer@test.com")

    def test_returns_stats(self):
        stats = ReferralService.get_referral_stats(self.referrer.id)
        profile = GuestProfile.objects.get(user=self.referrer)

        self.assertEqual(stats["referral_code"], profile.referral_code)
        self.assertEqual(stats["total_referred"], 0)
        self.assertEqual(stats["completed"], 0)
        self.assertEqual(stats["pending"], 0)
        self.assertEqual(stats["expired"], 0)

    def test_counts_correctly(self):
        for i in range(3):
            referred = _create_guest(f"ref{i}", f"ref{i}@test.com")
            profile = GuestProfile.objects.get(user=self.referrer)
            Referral.objects.create(
                referrer=self.referrer,
                referred_user=referred,
                referral_code_used=profile.referral_code,
                status=["pending", "completed", "expired"][i],
                reward_points_granted=50 if i == 1 else 0,
            )

        stats = ReferralService.get_referral_stats(self.referrer.id)
        self.assertEqual(stats["total_referred"], 3)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["expired"], 1)
        self.assertEqual(stats["total_bonus_points_earned"], 50)
