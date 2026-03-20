from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import GuestProfile, User
from apps.chatbot.models import Conversation, Message
from apps.chatbot.tools import CHATBOT_TOOLS, ToolExecutor
from apps.domotics.models import LockAccessCode, SmartDevice
from apps.loyalty.models import TierConfig
from apps.properties.models import Property, PropertyAmenity
from apps.reservations.models import Reservation


def _setup():
    TierConfig.objects.all().delete()
    TierConfig.objects.create(tier_name="bronze", min_reservations=0, min_referrals=0, discount_percent=0, sort_order=1)
    TierConfig.objects.create(tier_name="gold", min_reservations=8, min_referrals=3, discount_percent=10, sort_order=3)

    owner = User.objects.create_user(username="owner", email="o@t.com", password="t", role="owner")
    guest = User.objects.create_user(username="guest", email="g@t.com", password="t", role="guest")
    profile = GuestProfile.objects.get(user=guest)
    profile.loyalty_tier = "gold"
    profile.points_balance = 200
    profile.direct_bookings_count = 10
    profile.save()

    prop = Property.objects.create(
        owner=owner, name="Beach House", slug="beach-house",
        property_type="house", address="123 Ocean Dr", city="Miami",
        state="FL", zip_code="33139", status="active",
        base_nightly_rate=Decimal("250"), cleaning_fee=Decimal("100"),
        check_in_time=time(16, 0), check_out_time=time(11, 0),
        is_direct_booking_enabled=True, min_nights=2, max_nights=30,
        hostaway_raw_data={"houseRules": "No smoking", "wifiName": "BeachNet", "wifiPassword": "sun2025"},
    )
    PropertyAmenity.objects.create(property=prop, name="WiFi", category="essentials")
    PropertyAmenity.objects.create(property=prop, name="Pool", category="outdoor")

    res = Reservation.objects.create(
        property=prop, guest_user=guest, channel="direct", status="confirmed",
        confirmation_code="WS-TEST01",
        check_in_date=date.today() + timedelta(days=1),
        check_out_date=date.today() + timedelta(days=5),
        nights=4, guests_count=2, guest_name="Test Guest",
        nightly_rate=Decimal("250"), total_amount=Decimal("1100"),
    )

    return guest, prop, res


class TestToolDefinitions(TestCase):
    def test_tools_list_not_empty(self):
        self.assertGreater(len(CHATBOT_TOOLS), 0)

    def test_all_tools_have_required_fields(self):
        for tool in CHATBOT_TOOLS:
            self.assertEqual(tool["type"], "function")
            self.assertIn("name", tool["function"])
            self.assertIn("description", tool["function"])
            self.assertIn("parameters", tool["function"])


class TestToolExecutor(TestCase):
    def setUp(self):
        self.guest, self.prop, self.res = _setup()
        self.executor = ToolExecutor(self.guest.id, self.res.id)

    def test_check_availability_available(self):
        ci = (date.today() + timedelta(days=20)).isoformat()
        co = (date.today() + timedelta(days=25)).isoformat()
        result = self.executor.check_availability(self.prop.id, ci, co)
        self.assertIn("available", result.lower())

    def test_check_availability_unavailable(self):
        ci = self.res.check_in_date.isoformat()
        co = self.res.check_out_date.isoformat()
        result = self.executor.check_availability(self.prop.id, ci, co)
        self.assertIn("NOT available", result)

    def test_calculate_price(self):
        ci = (date.today() + timedelta(days=20)).isoformat()
        co = (date.today() + timedelta(days=25)).isoformat()
        result = self.executor.calculate_price(self.prop.id, ci, co)
        self.assertIn("250.00", result)
        self.assertIn("Gold", result)

    def test_get_access_code_with_code(self):
        lock = SmartDevice.objects.create(
            property=self.prop, device_type="smart_lock", brand="august",
            external_device_id="seam_1", display_name="Front Door", status="online",
        )
        LockAccessCode.objects.create(
            device=lock, reservation=self.res,
            code="847291", code_name="WS-TEST01 Front Door",
            status="active",
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=4),
        )

        result = self.executor.get_access_code()
        self.assertIn("847291", result)
        self.assertIn("Front Door", result)

    def test_get_access_code_no_code(self):
        result = self.executor.get_access_code()
        self.assertIn("no access code", result.lower())

    def test_get_access_code_no_reservation(self):
        executor = ToolExecutor(self.guest.id, reservation_id=None)
        result = executor.get_access_code()
        self.assertIn("No active reservation", result)

    def test_get_loyalty_info(self):
        result = self.executor.get_loyalty_info()
        self.assertIn("Gold", result)
        self.assertIn("200", result)

    def test_get_property_info(self):
        result = self.executor.get_property_info()
        self.assertIn("Beach House", result)
        self.assertIn("WiFi", result)
        self.assertIn("Pool", result)
        self.assertIn("No smoking", result)
        self.assertIn("BeachNet", result)

    def test_get_property_info_explicit_id(self):
        result = self.executor.get_property_info(property_id=self.prop.id)
        self.assertIn("Beach House", result)

    def test_get_property_info_not_found(self):
        result = self.executor.get_property_info(property_id=99999)
        self.assertIn("not found", result.lower())

    def test_escalate_to_human(self):
        Conversation.objects.create(
            guest=self.guest, reservation=self.res,
            channel="web", status="active",
        )

        result = self.executor.escalate_to_human("Guest wants refund")
        self.assertIn("support team", result.lower())

        conv = Conversation.objects.get(guest=self.guest)
        self.assertEqual(conv.status, "escalated")

        system_msg = Message.objects.filter(
            conversation=conv, sender_type="system",
        ).first()
        self.assertIsNotNone(system_msg)
        self.assertIn("refund", system_msg.content.lower())

    def test_execute_dispatches_correctly(self):
        result = self.executor.execute("get_loyalty_info", {})
        self.assertIn("Gold", result)

    def test_execute_unknown_function(self):
        result = self.executor.execute("nonexistent_function", {})
        self.assertIn("Unknown", result)

    def test_execute_handles_errors_gracefully(self):
        result = self.executor.execute("check_availability", {"property_id": 99999, "check_in": "2025-08-01", "check_out": "2025-08-05"})
        # Should not crash, returns error message
        self.assertIsInstance(result, str)
