from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import GuestProfile, User
from apps.loyalty.models import PointTransaction, TierConfig
from apps.loyalty.signal_handlers import on_reservation_cancelled
from apps.properties.models import Property
from apps.reservations.models import Reservation


def _create_guest():
    return User.objects.create_user(
        username="guest1", email="guest@test.com", password="test", role="guest",
    )


def _seed_tiers():
    TierConfig.objects.all().delete()
    TierConfig.objects.create(tier_name="bronze", min_reservations=0, min_referrals=0, discount_percent=0, sort_order=1)


class TestOnReservationCancelled(TestCase):
    def setUp(self):
        _seed_tiers()
        self.guest = _create_guest()
        owner = User.objects.create_user(
            username="owner", email="owner@test.com", password="test", role="owner",
        )
        self.prop = Property.objects.create(
            owner=owner, name="Villa", slug="villa",
            property_type="villa", address="123 St", city="Miami",
            state="FL", zip_code="33101", base_nightly_rate=Decimal("200.00"),
        )

    def test_refunds_redeemed_points(self):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.points_balance = 50
        profile.save()

        res = Reservation.objects.create(
            property=self.prop, guest_user=self.guest,
            channel="direct", status="cancelled",
            confirmation_code="WS-001", check_in_date=date(2025, 7, 1),
            check_out_date=date(2025, 7, 5), nights=4,
            guest_name="Test", nightly_rate=Decimal("200.00"),
            total_amount=Decimal("700.00"), points_redeemed=30,
            discount_amount=Decimal("30.00"),
        )

        on_reservation_cancelled(sender=Reservation, instance=res)

        profile.refresh_from_db()
        self.assertEqual(profile.points_balance, 80)  # 50 + 30

        res.refresh_from_db()
        self.assertEqual(res.points_redeemed, 0)
        self.assertEqual(res.discount_amount, 0)

        refund_tx = PointTransaction.objects.filter(
            guest=self.guest, transaction_type="adjust", points__gt=0,
        ).first()
        self.assertIsNotNone(refund_tx)
        self.assertEqual(refund_tx.points, 30)

    def test_reverses_earned_points(self):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.points_balance = 40
        profile.direct_bookings_count = 2
        profile.save()

        res = Reservation.objects.create(
            property=self.prop, guest_user=self.guest,
            channel="direct", status="cancelled",
            confirmation_code="WS-002", check_in_date=date(2025, 7, 1),
            check_out_date=date(2025, 7, 5), nights=4,
            guest_name="Test", nightly_rate=Decimal("200.00"),
            total_amount=Decimal("800.00"), points_earned=40,
        )

        on_reservation_cancelled(sender=Reservation, instance=res)

        profile.refresh_from_db()
        self.assertEqual(profile.points_balance, 0)
        self.assertEqual(profile.direct_bookings_count, 1)

    def test_clamps_negative_balance(self):
        """If guest already spent earned points, balance clamps to 0."""
        profile = GuestProfile.objects.get(user=self.guest)
        profile.points_balance = 10  # already spent 30 of the 40 earned
        profile.save()

        res = Reservation.objects.create(
            property=self.prop, guest_user=self.guest,
            channel="direct", status="cancelled",
            confirmation_code="WS-003", check_in_date=date(2025, 7, 1),
            check_out_date=date(2025, 7, 5), nights=4,
            guest_name="Test", nightly_rate=Decimal("200.00"),
            total_amount=Decimal("800.00"), points_earned=40,
        )

        on_reservation_cancelled(sender=Reservation, instance=res)

        profile.refresh_from_db()
        self.assertEqual(profile.points_balance, 0)

    def test_ignores_non_direct(self):
        res = Reservation.objects.create(
            property=self.prop, guest_user=self.guest,
            channel="airbnb", status="cancelled",
            confirmation_code="AIR-001", check_in_date=date(2025, 7, 1),
            check_out_date=date(2025, 7, 5), nights=4,
            guest_name="Test", nightly_rate=Decimal("200.00"),
            total_amount=Decimal("800.00"),
        )

        on_reservation_cancelled(sender=Reservation, instance=res)
        self.assertEqual(PointTransaction.objects.count(), 0)
