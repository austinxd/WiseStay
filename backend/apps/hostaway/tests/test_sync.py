import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.hostaway.models import SyncLog
from apps.hostaway.sync import HostawaySyncEngine
from apps.properties.models import (
    CalendarBlock,
    Property,
    PropertyAmenity,
    PropertyImage,
)
from apps.reservations.models import Reservation

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str):
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


class TestSyncListings(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner1", email="owner@test.com", password="test", role="owner",
        )
        self.admin = User.objects.create_user(
            username="admin1", email="admin@test.com", password="test", role="admin",
        )
        self.listing_fixture = _load_fixture("listing.json")
        self.engine = HostawaySyncEngine(triggered_by="test")

    @patch.object(HostawaySyncEngine, "_paginate_listings")
    def test_creates_new_property(self, mock_paginate):
        mock_paginate.return_value = [self.listing_fixture]

        with patch("apps.hostaway.sync.HostawayAPIClient"):
            sync_log = self.engine.sync_all_listings(
                owner_mapping={"98765": self.owner.id}
            )

        self.assertEqual(sync_log.status, "success")
        self.assertEqual(sync_log.items_processed, 1)

        prop = Property.objects.get(hostaway_listing_id="98765")
        self.assertEqual(prop.name, "Luxurious Malibu Beachfront Villa")
        self.assertEqual(prop.property_type, "villa")
        self.assertEqual(prop.city, "Malibu")
        self.assertEqual(prop.owner_id, self.owner.id)
        self.assertEqual(prop.base_nightly_rate, Decimal("895.00"))
        self.assertIsNotNone(prop.hostaway_last_synced_at)

    @patch.object(HostawaySyncEngine, "_paginate_listings")
    def test_creates_images_and_amenities(self, mock_paginate):
        mock_paginate.return_value = [self.listing_fixture]

        with patch("apps.hostaway.sync.HostawayAPIClient"):
            self.engine.sync_all_listings(owner_mapping={"98765": self.owner.id})

        prop = Property.objects.get(hostaway_listing_id="98765")
        self.assertEqual(PropertyImage.objects.filter(property=prop).count(), 4)
        self.assertTrue(
            PropertyImage.objects.filter(property=prop, is_cover=True).exists()
        )
        self.assertGreater(PropertyAmenity.objects.filter(property=prop).count(), 0)

    @patch.object(HostawaySyncEngine, "_paginate_listings")
    def test_updates_existing_property(self, mock_paginate):
        # Create existing property
        prop = Property.objects.create(
            owner=self.owner,
            hostaway_listing_id="98765",
            name="Old Name",
            slug="old-name",
            property_type="house",
            address="old addr",
            city="old city",
            state="CA",
            zip_code="00000",
            base_nightly_rate=Decimal("100.00"),
        )

        mock_paginate.return_value = [self.listing_fixture]
        with patch("apps.hostaway.sync.HostawayAPIClient"):
            sync_log = self.engine.sync_all_listings()

        prop.refresh_from_db()
        self.assertEqual(prop.name, "Luxurious Malibu Beachfront Villa")
        self.assertEqual(prop.slug, "old-name")  # Slug should NOT change
        self.assertEqual(prop.base_nightly_rate, Decimal("895.00"))

    @patch.object(HostawaySyncEngine, "_paginate_listings")
    def test_new_listing_no_owner_falls_back_to_admin(self, mock_paginate):
        mock_paginate.return_value = [self.listing_fixture]

        with patch("apps.hostaway.sync.HostawayAPIClient"):
            self.engine.sync_all_listings()  # No owner_mapping

        prop = Property.objects.get(hostaway_listing_id="98765")
        self.assertEqual(prop.owner_id, self.admin.id)

    @patch.object(HostawaySyncEngine, "_paginate_listings")
    def test_creates_sync_log(self, mock_paginate):
        mock_paginate.return_value = [self.listing_fixture]

        with patch("apps.hostaway.sync.HostawayAPIClient"):
            sync_log = self.engine.sync_all_listings(
                owner_mapping={"98765": self.owner.id}
            )

        self.assertEqual(sync_log.sync_type, "listings")
        self.assertEqual(sync_log.triggered_by, "test")
        self.assertIsNotNone(sync_log.completed_at)

    @patch.object(HostawaySyncEngine, "_paginate_listings")
    def test_handles_partial_failure(self, mock_paginate):
        bad_listing = {"id": 11111}  # Missing required fields to cause inner error
        mock_paginate.return_value = [self.listing_fixture, bad_listing]

        with patch("apps.hostaway.sync.HostawayAPIClient"):
            sync_log = self.engine.sync_all_listings(
                owner_mapping={"98765": self.owner.id}
            )

        self.assertIn(sync_log.status, ("partial", "success"))
        self.assertEqual(sync_log.items_processed, 2)


class TestSyncReservations(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner1", email="owner@test.com", password="test", role="owner",
        )
        self.guest = User.objects.create_user(
            username="guest1", email="sarah.johnson@example.com", password="test", role="guest",
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
        self.res_fixture = _load_fixture("reservation.json")
        self.engine = HostawaySyncEngine(triggered_by="test")

    @patch.object(HostawaySyncEngine, "_paginate_reservations")
    def test_creates_new_reservation(self, mock_paginate):
        mock_paginate.return_value = [self.res_fixture]

        with patch("apps.hostaway.sync.HostawayAPIClient"):
            sync_log = self.engine.sync_reservations(
                modified_since=timezone.now() - timedelta(days=1)
            )

        self.assertEqual(sync_log.status, "success")
        self.assertEqual(sync_log.items_created, 1)

        res = Reservation.objects.get(hostaway_reservation_id="54321")
        self.assertEqual(res.channel, "airbnb")
        self.assertEqual(res.status, "confirmed")
        self.assertEqual(res.guest_name, "Sarah Johnson")
        self.assertEqual(res.property_id, self.prop.id)

    @patch.object(HostawaySyncEngine, "_paginate_reservations")
    def test_matches_guest_by_email(self, mock_paginate):
        mock_paginate.return_value = [self.res_fixture]

        with patch("apps.hostaway.sync.HostawayAPIClient"):
            self.engine.sync_reservations(
                modified_since=timezone.now() - timedelta(days=1)
            )

        res = Reservation.objects.get(hostaway_reservation_id="54321")
        self.assertEqual(res.guest_user_id, self.guest.id)

    @patch.object(HostawaySyncEngine, "_paginate_reservations")
    def test_updates_existing_reservation(self, mock_paginate):
        Reservation.objects.create(
            property=self.prop,
            hostaway_reservation_id="54321",
            channel="airbnb",
            status="pending",
            confirmation_code="HMAB12XYZ9",
            check_in_date=date(2025, 7, 15),
            check_out_date=date(2025, 7, 20),
            nights=5,
            guest_name="Sarah Johnson",
            nightly_rate=Decimal("895.00"),
            total_amount=Decimal("5225.00"),
        )

        mock_paginate.return_value = [self.res_fixture]
        with patch("apps.hostaway.sync.HostawayAPIClient"):
            sync_log = self.engine.sync_reservations(
                modified_since=timezone.now() - timedelta(days=1)
            )

        self.assertEqual(sync_log.items_updated, 1)
        res = Reservation.objects.get(hostaway_reservation_id="54321")
        self.assertEqual(res.status, "confirmed")

    @patch.object(HostawaySyncEngine, "_paginate_reservations")
    def test_protects_wisestay_fields_on_direct(self, mock_paginate):
        """Direct reservations with Stripe payment should not have financial fields overwritten."""
        Reservation.objects.create(
            property=self.prop,
            hostaway_reservation_id="54321",
            channel="direct",
            status="confirmed",
            confirmation_code="WS-DIRECT1",
            check_in_date=date(2025, 7, 15),
            check_out_date=date(2025, 7, 20),
            nights=5,
            guest_name="Sarah Johnson",
            nightly_rate=Decimal("850.00"),
            total_amount=Decimal("5000.00"),
            discount_amount=Decimal("100.00"),
            points_earned=25,
            points_redeemed=10,
            stripe_payment_intent_id="pi_test123",
        )

        # Hostaway reports different financial data
        self.res_fixture["channelId"] = 2005
        mock_paginate.return_value = [self.res_fixture]

        with patch("apps.hostaway.sync.HostawayAPIClient"):
            self.engine.sync_reservations(
                modified_since=timezone.now() - timedelta(days=1)
            )

        res = Reservation.objects.get(hostaway_reservation_id="54321")
        # WiseStay fields should be PRESERVED
        self.assertEqual(res.discount_amount, Decimal("100.00"))
        self.assertEqual(res.points_earned, 25)
        self.assertEqual(res.points_redeemed, 10)
        self.assertEqual(res.stripe_payment_intent_id, "pi_test123")
        self.assertEqual(res.total_amount, Decimal("5000.00"))
        self.assertEqual(res.confirmation_code, "WS-DIRECT1")

    @patch.object(HostawaySyncEngine, "_paginate_reservations")
    def test_fires_confirmed_signal_on_create(self, mock_paginate):
        mock_paginate.return_value = [self.res_fixture]
        signal_received = []

        from apps.hostaway.signals import reservation_confirmed

        def handler(sender, **kwargs):
            signal_received.append(kwargs)

        reservation_confirmed.connect(handler)
        try:
            with patch("apps.hostaway.sync.HostawayAPIClient"):
                self.engine.sync_reservations(
                    modified_since=timezone.now() - timedelta(days=1)
                )
            self.assertEqual(len(signal_received), 1)
            self.assertTrue(signal_received[0]["created"])
        finally:
            reservation_confirmed.disconnect(handler)


class TestSyncCalendar(TestCase):
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
            status="active",
            address="123 Test St",
            city="Malibu",
            state="CA",
            zip_code="90265",
            base_nightly_rate=Decimal("895.00"),
        )
        self.calendar_fixture = _load_fixture("calendar.json")
        self.engine = HostawaySyncEngine(triggered_by="test")

    def test_creates_calendar_blocks(self):
        mock_client = MagicMock()
        mock_client.get_calendar.return_value = self.calendar_fixture
        self.engine.client = mock_client

        sync_log = self.engine.sync_calendar(property_id=self.prop.id)

        blocks = CalendarBlock.objects.filter(
            property=self.prop, block_type="hostaway_sync"
        )
        self.assertEqual(blocks.count(), 2)
        self.assertEqual(sync_log.status, "success")

    def test_replaces_old_sync_blocks(self):
        today = date.today()
        # Create existing sync block within the sync range (should be replaced)
        CalendarBlock.objects.create(
            property=self.prop,
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=15),
            block_type="hostaway_sync",
        )
        # Create owner block that should NOT be removed
        CalendarBlock.objects.create(
            property=self.prop,
            start_date=today + timedelta(days=20),
            end_date=today + timedelta(days=25),
            block_type="owner_block",
        )

        mock_client = MagicMock()
        mock_client.get_calendar.return_value = self.calendar_fixture
        self.engine.client = mock_client

        self.engine.sync_calendar(property_id=self.prop.id)

        # hostaway_sync blocks should be the new ones from the fixture
        sync_blocks = CalendarBlock.objects.filter(
            property=self.prop, block_type="hostaway_sync"
        )
        self.assertEqual(sync_blocks.count(), 2)

        # Owner block should still exist
        owner_blocks = CalendarBlock.objects.filter(
            property=self.prop, block_type="owner_block"
        )
        self.assertEqual(owner_blocks.count(), 1)


class TestPushDirectReservation(TestCase):
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
            channel="direct",
            status="confirmed",
            confirmation_code="WS-TEST01",
            check_in_date=date(2025, 8, 10),
            check_out_date=date(2025, 8, 15),
            nights=5,
            guests_count=2,
            guest_name="John Doe",
            guest_email="john@example.com",
            nightly_rate=Decimal("895.00"),
            total_amount=Decimal("4725.00"),
            stripe_payment_intent_id="pi_abc123",
        )
        self.engine = HostawaySyncEngine(triggered_by="test")

    def test_pushes_and_saves_hostaway_id(self):
        mock_client = MagicMock()
        mock_client.create_reservation.return_value = {"id": 88888}
        self.engine.client = mock_client

        ha_id = self.engine.push_direct_reservation_to_hostaway(self.reservation.id)

        self.assertEqual(ha_id, 88888)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.hostaway_reservation_id, "88888")

    def test_builds_correct_payload(self):
        mock_client = MagicMock()
        mock_client.create_reservation.return_value = {"id": 88888}
        self.engine.client = mock_client

        self.engine.push_direct_reservation_to_hostaway(self.reservation.id)

        payload = mock_client.create_reservation.call_args[0][0]
        self.assertEqual(payload["listingMapId"], 98765)
        self.assertEqual(payload["channelId"], 2005)
        self.assertEqual(payload["source"], "WiseStay Direct")
        self.assertEqual(payload["guestName"], "John Doe")
        self.assertEqual(payload["guestFirstName"], "John")
        self.assertEqual(payload["guestLastName"], "Doe")
        self.assertEqual(payload["arrivalDate"], "2025-08-10")
        self.assertEqual(payload["departureDate"], "2025-08-15")
        self.assertEqual(payload["totalPrice"], 4725.00)
        self.assertEqual(payload["status"], "confirmed")
        self.assertEqual(payload["isPaid"], 1)

    def test_rejects_non_direct_reservation(self):
        self.reservation.channel = "airbnb"
        self.reservation.save()

        with self.assertRaises(ValueError) as ctx:
            self.engine.push_direct_reservation_to_hostaway(self.reservation.id)
        self.assertIn("not a direct booking", str(ctx.exception))

    def test_skips_if_already_pushed(self):
        self.reservation.hostaway_reservation_id = "77777"
        self.reservation.save()

        mock_client = MagicMock()
        self.engine.client = mock_client

        ha_id = self.engine.push_direct_reservation_to_hostaway(self.reservation.id)
        self.assertEqual(ha_id, 77777)
        mock_client.create_reservation.assert_not_called()
