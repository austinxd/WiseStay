from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.accounts.models import GuestProfile, User
from apps.loyalty.models import PointTransaction, TierConfig
from apps.payments.models import PaymentRecord
from apps.properties.models import Property
from apps.reservations.models import Reservation
from apps.reservations.services import ReservationService


def _seed_tiers():
    TierConfig.objects.all().delete()
    TierConfig.objects.create(tier_name="bronze", min_reservations=0, min_referrals=0, discount_percent=0, sort_order=1)


def _setup():
    _seed_tiers()
    owner = User.objects.create_user(username="owner", email="owner@t.com", password="t", role="owner")
    guest = User.objects.create_user(username="guest", email="guest@t.com", password="t", role="guest")
    prop = Property.objects.create(
        owner=owner, name="Villa", slug="villa", property_type="villa",
        address="123 St", city="Miami", state="FL", zip_code="33139",
        status="active", base_nightly_rate=Decimal("200"),
        cleaning_fee=Decimal("100"), is_direct_booking_enabled=True,
        min_nights=1, max_nights=30,
    )
    return owner, guest, prop


class TestInitiateDirectBooking(TestCase):
    def setUp(self):
        self.owner, self.guest, self.prop = _setup()
        self.ci = date.today() + timedelta(days=10)
        self.co = self.ci + timedelta(days=3)

    @patch("stripe.PaymentIntent.create")
    def test_creates_reservation_and_payment_intent(self, mock_pi_create):
        mock_pi = MagicMock()
        mock_pi.id = "pi_test_123"
        mock_pi.client_secret = "pi_test_123_secret_abc"
        mock_pi_create.return_value = mock_pi

        result = ReservationService.initiate_direct_booking(
            guest_user_id=self.guest.id,
            property_id=self.prop.id,
            check_in=self.ci,
            check_out=self.co,
            guests_count=2,
        )

        self.assertIn("reservation_id", result)
        self.assertIn("stripe_client_secret", result)
        self.assertEqual(result["stripe_client_secret"], "pi_test_123_secret_abc")

        res = Reservation.objects.get(pk=result["reservation_id"])
        self.assertEqual(res.status, "pending")
        self.assertEqual(res.channel, "direct")
        self.assertEqual(res.stripe_payment_intent_id, "pi_test_123")
        self.assertTrue(res.confirmation_code.startswith("WS-"))

        pr = PaymentRecord.objects.get(reservation=res)
        self.assertEqual(pr.status, "pending")
        self.assertEqual(pr.payment_type, "charge")

    @patch("stripe.PaymentIntent.create")
    def test_unavailable_dates_raises(self, mock_pi_create):
        Reservation.objects.create(
            property=self.prop, channel="airbnb", status="confirmed",
            confirmation_code="AIR-001",
            check_in_date=self.ci, check_out_date=self.co,
            nights=3, guest_name="Existing",
            nightly_rate=Decimal("200"), total_amount=Decimal("600"),
        )

        with self.assertRaises(ValueError) as ctx:
            ReservationService.initiate_direct_booking(
                self.guest.id, self.prop.id, self.ci, self.co, 2,
            )
        self.assertIn("not available", str(ctx.exception))


class TestConfirmBooking(TestCase):
    def setUp(self):
        self.owner, self.guest, self.prop = _setup()

    def _create_pending_reservation(self):
        res = Reservation.objects.create(
            property=self.prop, guest_user=self.guest,
            channel="direct", status="pending",
            confirmation_code="WS-TEST01",
            check_in_date=date.today() + timedelta(days=10),
            check_out_date=date.today() + timedelta(days=13),
            nights=3, guests_count=2, guest_name="Test",
            nightly_rate=Decimal("200"), total_amount=Decimal("700"),
            stripe_payment_intent_id="pi_test_123",
        )
        PaymentRecord.objects.create(
            reservation=res, payment_type="charge", status="pending",
            amount=Decimal("700"), payment_intent_id="pi_test_123",
        )
        return res

    @patch("apps.hostaway.tasks.push_reservation_to_hostaway.delay")
    def test_confirms_reservation(self, mock_push):
        res = self._create_pending_reservation()
        result = ReservationService.confirm_booking(res.id, "pi_test_123")

        self.assertEqual(result.status, "confirmed")
        self.assertIsNotNone(result.confirmed_at)

        pr = PaymentRecord.objects.get(reservation=res, payment_type="charge")
        self.assertEqual(pr.status, "succeeded")

    @patch("apps.hostaway.tasks.push_reservation_to_hostaway.delay")
    def test_idempotent(self, mock_push):
        res = self._create_pending_reservation()
        ReservationService.confirm_booking(res.id, "pi_test_123")
        result = ReservationService.confirm_booking(res.id, "pi_test_123")
        self.assertEqual(result.status, "confirmed")

    @patch("apps.hostaway.tasks.push_reservation_to_hostaway.delay")
    def test_pushes_to_hostaway(self, mock_push):
        res = self._create_pending_reservation()
        ReservationService.confirm_booking(res.id, "pi_test_123")
        mock_push.assert_called_once_with(res.id)

    def test_rejects_wrong_pi_id(self):
        res = self._create_pending_reservation()
        with self.assertRaises(ValueError):
            ReservationService.confirm_booking(res.id, "pi_wrong")


class TestCancelBooking(TestCase):
    def setUp(self):
        self.owner, self.guest, self.prop = _setup()

    @patch("stripe.Refund.create")
    def test_cancels_and_refunds(self, mock_refund_create):
        mock_refund = MagicMock()
        mock_refund.id = "re_test_123"
        mock_refund_create.return_value = mock_refund

        res = Reservation.objects.create(
            property=self.prop, guest_user=self.guest,
            channel="direct", status="confirmed",
            confirmation_code="WS-CANCEL1",
            check_in_date=date.today() + timedelta(days=10),
            check_out_date=date.today() + timedelta(days=13),
            nights=3, guest_name="Test",
            nightly_rate=Decimal("200"), total_amount=Decimal("700"),
            stripe_payment_intent_id="pi_cancel_123",
        )
        PaymentRecord.objects.create(
            reservation=res, payment_type="charge", status="succeeded",
            amount=Decimal("700"), payment_intent_id="pi_cancel_123",
        )

        result = ReservationService.cancel_booking(res.id, "guest", "Plans changed")

        self.assertEqual(result.status, "cancelled")
        self.assertIsNotNone(result.cancelled_at)

        refund_record = PaymentRecord.objects.filter(
            reservation=res, payment_type="refund",
        ).first()
        self.assertIsNotNone(refund_record)
        self.assertEqual(refund_record.status, "succeeded")

    def test_cannot_cancel_checked_in(self):
        res = Reservation.objects.create(
            property=self.prop, guest_user=self.guest,
            channel="direct", status="checked_in",
            confirmation_code="WS-CI01",
            check_in_date=date.today(), check_out_date=date.today() + timedelta(days=3),
            nights=3, guest_name="Test",
            nightly_rate=Decimal("200"), total_amount=Decimal("600"),
        )
        with self.assertRaises(ValueError):
            ReservationService.cancel_booking(res.id)


class TestConfirmationCode(TestCase):
    def test_generates_unique_codes(self):
        codes = set()
        for _ in range(20):
            code = ReservationService.generate_confirmation_code()
            self.assertTrue(code.startswith("WS-"))
            self.assertEqual(len(code), 9)
            codes.add(code)
        self.assertEqual(len(codes), 20)
