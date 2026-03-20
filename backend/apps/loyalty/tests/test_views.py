from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import GuestProfile, User
from apps.loyalty.models import PointTransaction, Referral, TierConfig
from apps.properties.models import Property
from apps.reservations.models import Reservation


def _seed_tiers():
    TierConfig.objects.all().delete()
    TierConfig.objects.create(tier_name="bronze", min_reservations=0, min_referrals=0, discount_percent=0, sort_order=1)
    TierConfig.objects.create(tier_name="silver", min_reservations=3, min_referrals=1, discount_percent=5, sort_order=2)
    TierConfig.objects.create(tier_name="gold", min_reservations=8, min_referrals=3, discount_percent=10, sort_order=3, early_checkin=True, late_checkout=True, priority_support=True)


class TestLoyaltyDashboard(TestCase):
    def setUp(self):
        _seed_tiers()
        self.guest = User.objects.create_user(
            username="guest", email="guest@test.com", password="test", role="guest",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.guest)

    def test_returns_dashboard(self):
        response = self.api.get("/api/v1/loyalty/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tier"], "bronze")
        self.assertIn("points_balance", response.data)
        self.assertIn("referral_code", response.data)

    def test_unauthenticated_rejected(self):
        self.api.force_authenticate(user=None)
        response = self.api.get("/api/v1/loyalty/dashboard/")
        self.assertEqual(response.status_code, 401)

    def test_non_guest_rejected(self):
        owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="test", role="owner",
        )
        self.api.force_authenticate(user=owner)
        response = self.api.get("/api/v1/loyalty/dashboard/")
        self.assertEqual(response.status_code, 403)


class TestPointsHistory(TestCase):
    def setUp(self):
        self.guest = User.objects.create_user(
            username="guest", email="guest@test.com", password="test", role="guest",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.guest)

        # Create some transactions
        for i in range(3):
            PointTransaction.objects.create(
                guest=self.guest,
                transaction_type="earn",
                points=10,
                balance_after=10 * (i + 1),
                description=f"Test earn {i}",
            )

    def test_lists_transactions(self):
        response = self.api.get("/api/v1/loyalty/points/history/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)

    def test_filters_by_type(self):
        PointTransaction.objects.create(
            guest=self.guest, transaction_type="redeem",
            points=-5, balance_after=25, description="Test redeem",
        )

        response = self.api.get("/api/v1/loyalty/points/history/?type=redeem")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)


class TestRedeemPoints(TestCase):
    def setUp(self):
        _seed_tiers()
        self.guest = User.objects.create_user(
            username="guest", email="guest@test.com", password="test", role="guest",
        )
        profile = GuestProfile.objects.get(user=self.guest)
        profile.points_balance = 100
        profile.save()

        # Create earn transaction to back the balance
        PointTransaction.objects.create(
            guest=self.guest, transaction_type="earn",
            points=100, points_remaining=100,
            balance_after=100, description="Seed",
            expires_at=timezone.now() + timedelta(days=365),
        )

        owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="test", role="owner",
        )
        self.prop = Property.objects.create(
            owner=owner, name="Villa", slug="villa",
            property_type="villa", address="123 St", city="Miami",
            state="FL", zip_code="33101", base_nightly_rate=Decimal("200.00"),
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.guest)

    def test_redeems_points(self):
        res = Reservation.objects.create(
            property=self.prop, guest_user=self.guest,
            channel="direct", status="pending",
            confirmation_code="WS-001",
            check_in_date=date(2025, 7, 1), check_out_date=date(2025, 7, 5),
            nights=4, guest_name="Test", nightly_rate=Decimal("200.00"),
            total_amount=Decimal("800.00"),
        )

        response = self.api.post("/api/v1/loyalty/points/redeem/", {
            "points": 30,
            "reservation_id": res.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["discount_amount"], 30.0)
        self.assertEqual(response.data["new_balance"], 70)

    def test_rejects_insufficient_points(self):
        response = self.api.post("/api/v1/loyalty/points/redeem/", {"points": 200})
        self.assertEqual(response.status_code, 400)

    def test_rejects_zero_points(self):
        response = self.api.post("/api/v1/loyalty/points/redeem/", {"points": 0})
        self.assertEqual(response.status_code, 400)


class TestCalculateDiscount(TestCase):
    def setUp(self):
        _seed_tiers()
        self.guest = User.objects.create_user(
            username="guest", email="guest@test.com", password="test", role="guest",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.guest)

    def test_calculates_discount(self):
        response = self.api.post("/api/v1/loyalty/calculate-discount/", {
            "base_amount": "500.00",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("tier_discount_amount", response.data)
        self.assertIn("max_points_redeemable", response.data)

    def test_rejects_invalid_amount(self):
        response = self.api.post("/api/v1/loyalty/calculate-discount/", {
            "base_amount": "0.00",
        })
        self.assertEqual(response.status_code, 400)


class TestReferralEndpoints(TestCase):
    def setUp(self):
        self.referrer = User.objects.create_user(
            username="referrer", email="referrer@test.com", password="test", role="guest",
        )
        self.referred = User.objects.create_user(
            username="referred", email="referred@test.com", password="test", role="guest",
        )
        self.api = APIClient()

    def test_get_referral_info(self):
        self.api.force_authenticate(user=self.referrer)
        response = self.api.get("/api/v1/loyalty/referrals/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("referral_code", response.data)

    def test_apply_referral_code(self):
        referrer_profile = GuestProfile.objects.get(user=self.referrer)
        self.api.force_authenticate(user=self.referred)

        response = self.api.post("/api/v1/loyalty/referrals/apply/", {
            "referral_code": referrer_profile.referral_code,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "pending")

    def test_apply_invalid_code(self):
        self.api.force_authenticate(user=self.referred)
        response = self.api.post("/api/v1/loyalty/referrals/apply/", {
            "referral_code": "WS-FAKE",
        })
        self.assertEqual(response.status_code, 400)


class TestTierInfoEndpoint(TestCase):
    def setUp(self):
        _seed_tiers()
        self.api = APIClient()

    def test_public_access(self):
        response = self.api.get("/api/v1/loyalty/tiers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 3)  # bronze, silver, gold

    def test_returns_tier_details(self):
        response = self.api.get("/api/v1/loyalty/tiers/")
        tiers_by_name = {t["tier_name"]: t for t in response.data}
        self.assertEqual(tiers_by_name["gold"]["discount_percent"], "10.00")
        self.assertTrue(tiers_by_name["gold"]["early_checkin"])
