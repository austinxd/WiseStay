from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import GuestProfile, User
from apps.loyalty.models import TierConfig
from apps.properties.models import Property
from apps.reservations.pricing import PricingService


def _seed_tiers():
    TierConfig.objects.all().delete()
    TierConfig.objects.create(tier_name="bronze", min_reservations=0, min_referrals=0, discount_percent=0, sort_order=1)
    TierConfig.objects.create(tier_name="gold", min_reservations=8, min_referrals=3, discount_percent=10, sort_order=3)


class TestPricingService(TestCase):
    def setUp(self):
        _seed_tiers()
        self.owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="test", role="owner",
        )
        self.prop = Property.objects.create(
            owner=self.owner, name="Villa", slug="villa",
            property_type="villa", address="123 St", city="Miami",
            state="FL", zip_code="33139",
            base_nightly_rate=Decimal("200.00"),
            cleaning_fee=Decimal("100.00"),
        )
        self.ci = date.today() + timedelta(days=10)
        self.co = self.ci + timedelta(days=5)

    def test_basic_price_calculation(self):
        result = PricingService.calculate_price(self.prop.id, self.ci, self.co)

        self.assertEqual(result["nights"], 5)
        self.assertEqual(result["nightly_rate"], 200.00)
        self.assertEqual(result["subtotal"], 1000.00)  # 200 * 5
        self.assertEqual(result["cleaning_fee"], 100.00)
        self.assertEqual(result["service_fee"], 100.00)  # 10% of 1000
        self.assertEqual(result["taxes"], 0.00)
        self.assertEqual(result["gross_total"], 1200.00)

    def test_price_without_guest(self):
        result = PricingService.calculate_price(self.prop.id, self.ci, self.co)
        self.assertIsNone(result["tier_discount"])
        self.assertIsNone(result["loyalty"])

    def test_price_with_bronze_guest(self):
        guest = User.objects.create_user(
            username="guest", email="g@test.com", password="test", role="guest",
        )
        result = PricingService.calculate_price(self.prop.id, self.ci, self.co, guest.id)

        # Bronze has 0% discount
        self.assertEqual(result["total_before_points"], 1200.00)

    def test_price_with_gold_guest(self):
        guest = User.objects.create_user(
            username="guest", email="g@test.com", password="test", role="guest",
        )
        profile = GuestProfile.objects.get(user=guest)
        profile.loyalty_tier = "gold"
        profile.points_balance = 100
        profile.save()

        result = PricingService.calculate_price(self.prop.id, self.ci, self.co, guest.id)

        # Gold = 10% of subtotal (1000) = $100 discount
        self.assertIsNotNone(result["tier_discount"])
        self.assertEqual(result["tier_discount"]["percent"], 10)
        self.assertEqual(result["tier_discount"]["amount"], 100.00)
        self.assertEqual(result["total_before_points"], 1100.00)

    def test_calculate_final_amount_with_points(self):
        guest = User.objects.create_user(
            username="guest", email="g@test.com", password="test", role="guest",
        )
        profile = GuestProfile.objects.get(user=guest)
        profile.points_balance = 200
        profile.save()

        result = PricingService.calculate_final_amount(
            self.prop.id, self.ci, self.co, guest.id, points_to_redeem=50,
        )

        self.assertEqual(result["points_to_redeem"], 50)
        self.assertEqual(result["points_discount"], 50.00)
        self.assertEqual(result["charge_amount"], 1150.00)  # 1200 - 50

    def test_final_amount_respects_50_percent_floor(self):
        guest = User.objects.create_user(
            username="guest", email="g@test.com", password="test", role="guest",
        )
        profile = GuestProfile.objects.get(user=guest)
        profile.loyalty_tier = "gold"
        profile.points_balance = 1000
        profile.save()

        result = PricingService.calculate_final_amount(
            self.prop.id, self.ci, self.co, guest.id, points_to_redeem=1000,
        )

        # Gross = 1200, 50% floor = 600
        # Gold discount = 100, max points = 1200 - 600 - 100 = 500
        self.assertGreaterEqual(result["charge_amount"], 600.00)
