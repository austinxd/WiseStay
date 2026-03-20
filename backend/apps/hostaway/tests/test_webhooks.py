import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.test import TestCase

from apps.accounts.models import User
from apps.chatbot.models import Conversation, Message
from apps.hostaway.webhooks import (
    process_message_received,
    process_reservation_created,
    process_reservation_updated,
)
from apps.properties.models import Property
from apps.reservations.models import Reservation

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str):
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


class TestProcessReservationCreated(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner1", email="owner@test.com", password="test", role="owner",
        )
        self.prop = Property.objects.create(
            owner=self.owner,
            hostaway_listing_id="98765",
            name="Test Villa",
            slug="test-villa",
            property_type="villa",
            address="123 Test St",
            city="Malibu",
            state="CA",
            zip_code="90265",
            base_nightly_rate=Decimal("895.00"),
        )
        self.payload = _load_fixture("webhook_reservation_created.json")

    def test_creates_reservation(self):
        process_reservation_created(self.payload)

        res = Reservation.objects.get(hostaway_reservation_id="77001")
        self.assertEqual(res.channel, "booking")
        self.assertEqual(res.status, "confirmed")
        self.assertEqual(res.guest_name, "Marco Rossi")
        self.assertEqual(res.property_id, self.prop.id)
        self.assertEqual(res.check_in_date, date(2025, 8, 1))
        self.assertEqual(res.check_out_date, date(2025, 8, 5))

    def test_idempotent_duplicate(self):
        process_reservation_created(self.payload)
        process_reservation_created(self.payload)  # Second call

        self.assertEqual(
            Reservation.objects.filter(hostaway_reservation_id="77001").count(), 1
        )

    def test_matches_guest_by_email(self):
        guest = User.objects.create_user(
            username="marco", email="marco.rossi@example.it", password="test", role="guest",
        )
        process_reservation_created(self.payload)

        res = Reservation.objects.get(hostaway_reservation_id="77001")
        self.assertEqual(res.guest_user_id, guest.id)

    def test_unknown_property_logs_error(self):
        self.payload["data"]["listingMapId"] = 99999
        process_reservation_created(self.payload)

        self.assertFalse(
            Reservation.objects.filter(hostaway_reservation_id="77001").exists()
        )

    def test_fires_confirmed_signal(self):
        from apps.hostaway.signals import reservation_confirmed

        signals = []

        def handler(sender, **kwargs):
            signals.append(kwargs)

        reservation_confirmed.connect(handler)
        try:
            process_reservation_created(self.payload)
            self.assertEqual(len(signals), 1)
            self.assertTrue(signals[0]["created"])
        finally:
            reservation_confirmed.disconnect(handler)


class TestProcessReservationUpdated(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner1", email="owner@test.com", password="test", role="owner",
        )
        self.prop = Property.objects.create(
            owner=self.owner,
            hostaway_listing_id="98765",
            name="Test Villa",
            slug="test-villa",
            property_type="villa",
            address="123 Test St",
            city="Malibu",
            state="CA",
            zip_code="90265",
            base_nightly_rate=Decimal("895.00"),
        )
        self.reservation = Reservation.objects.create(
            property=self.prop,
            hostaway_reservation_id="77001",
            channel="booking",
            status="confirmed",
            confirmation_code="3847291056",
            check_in_date=date(2025, 8, 1),
            check_out_date=date(2025, 8, 5),
            nights=4,
            guest_name="Marco Rossi",
            nightly_rate=Decimal("895.00"),
            total_amount=Decimal("3830.00"),
        )

    def test_updates_status(self):
        payload = _load_fixture("webhook_reservation_created.json")
        payload["data"]["status"] = "cancelled"

        process_reservation_updated(payload)

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, "cancelled")

    def test_fires_cancelled_signal(self):
        from apps.hostaway.signals import reservation_cancelled

        signals = []

        def handler(sender, **kwargs):
            signals.append(True)

        reservation_cancelled.connect(handler)
        try:
            payload = _load_fixture("webhook_reservation_created.json")
            payload["data"]["status"] = "cancelled"
            process_reservation_updated(payload)

            self.assertEqual(len(signals), 1)
        finally:
            reservation_cancelled.disconnect(handler)

    def test_protects_direct_booking_financials(self):
        self.reservation.channel = "direct"
        self.reservation.stripe_payment_intent_id = "pi_test"
        self.reservation.discount_amount = Decimal("50.00")
        self.reservation.save()

        payload = _load_fixture("webhook_reservation_created.json")
        payload["data"]["id"] = 77001
        payload["data"]["totalPrice"] = 9999.00  # Should NOT overwrite

        process_reservation_updated(payload)

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.total_amount, Decimal("3830.00"))
        self.assertEqual(self.reservation.discount_amount, Decimal("50.00"))

    def test_nonexistent_reservation_creates_it(self):
        Reservation.objects.all().delete()
        payload = _load_fixture("webhook_reservation_created.json")

        process_reservation_updated(payload)

        self.assertTrue(
            Reservation.objects.filter(hostaway_reservation_id="77001").exists()
        )

    def test_fires_dates_changed_signal(self):
        from apps.hostaway.signals import reservation_dates_changed

        signals = []

        def handler(sender, **kwargs):
            signals.append(kwargs)

        reservation_dates_changed.connect(handler)
        try:
            payload = _load_fixture("webhook_reservation_created.json")
            payload["data"]["id"] = 77001
            payload["data"]["arrivalDate"] = "2025-08-05"
            payload["data"]["departureDate"] = "2025-08-10"

            process_reservation_updated(payload)

            self.assertEqual(len(signals), 1)
            self.assertEqual(signals[0]["old_check_in"], date(2025, 8, 1))
            self.assertEqual(signals[0]["old_check_out"], date(2025, 8, 5))
        finally:
            reservation_dates_changed.disconnect(handler)


class TestProcessMessageReceived(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner1", email="owner@test.com", password="test", role="owner",
        )
        self.guest = User.objects.create_user(
            username="guest1", email="guest@test.com", password="test", role="guest",
        )
        self.prop = Property.objects.create(
            owner=self.owner,
            hostaway_listing_id="98765",
            name="Test Villa",
            slug="test-villa",
            property_type="villa",
            address="123 Test St",
            city="Malibu",
            state="CA",
            zip_code="90265",
            base_nightly_rate=Decimal("895.00"),
        )
        self.reservation = Reservation.objects.create(
            property=self.prop,
            guest_user=self.guest,
            hostaway_reservation_id="77001",
            channel="booking",
            status="confirmed",
            confirmation_code="3847291056",
            check_in_date=date(2025, 8, 1),
            check_out_date=date(2025, 8, 5),
            nights=4,
            guest_name="Test Guest",
            nightly_rate=Decimal("895.00"),
            total_amount=Decimal("3830.00"),
        )

    def test_creates_conversation_and_message(self):
        payload = {
            "event": "conversationMessageCreated",
            "data": {
                "reservationId": "77001",
                "body": "What time can I check in?",
            },
        }

        process_message_received(payload)

        conv = Conversation.objects.get(guest=self.guest, reservation=self.reservation)
        self.assertEqual(conv.status, "active")
        msg = Message.objects.get(conversation=conv)
        self.assertEqual(msg.sender_type, "guest")
        self.assertEqual(msg.content, "What time can I check in?")

    def test_skips_if_reservation_not_found(self):
        payload = {
            "data": {"reservationId": "99999", "body": "Hello"},
        }

        process_message_received(payload)  # Should not raise
        self.assertEqual(Conversation.objects.count(), 0)

    def test_skips_if_no_guest_user(self):
        self.reservation.guest_user = None
        self.reservation.save()

        payload = {
            "data": {"reservationId": "77001", "body": "Hello"},
        }

        process_message_received(payload)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_reuses_existing_conversation(self):
        conv = Conversation.objects.create(
            guest=self.guest, reservation=self.reservation, channel="whatsapp",
        )

        payload = {
            "data": {"reservationId": "77001", "body": "First msg"},
        }
        process_message_received(payload)

        payload["data"]["body"] = "Second msg"
        process_message_received(payload)

        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.filter(conversation=conv).count(), 2)
