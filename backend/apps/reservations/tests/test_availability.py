from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.properties.models import CalendarBlock, Property
from apps.reservations.availability import AvailabilityService
from apps.reservations.models import Reservation


def _create_property(**kwargs):
    owner = User.objects.create_user(
        username="owner", email="owner@test.com", password="test", role="owner",
    )
    defaults = {
        "owner": owner, "name": "Test", "slug": "test-prop",
        "property_type": "house", "address": "123 St", "city": "Miami",
        "state": "FL", "zip_code": "33139", "status": "active",
        "base_nightly_rate": Decimal("200"), "is_direct_booking_enabled": True,
        "min_nights": 2, "max_nights": 30,
    }
    defaults.update(kwargs)
    return Property.objects.create(**defaults)


class TestCheckAvailability(TestCase):
    def setUp(self):
        self.prop = _create_property()
        self.ci = date.today() + timedelta(days=10)
        self.co = self.ci + timedelta(days=5)

    def test_available(self):
        result = AvailabilityService.check_availability(self.prop.id, self.ci, self.co)
        self.assertTrue(result["available"])
        self.assertEqual(result["nights"], 5)

    def test_blocked_by_reservation(self):
        Reservation.objects.create(
            property=self.prop, channel="airbnb", status="confirmed",
            confirmation_code="AIR-001",
            check_in_date=self.ci + timedelta(days=1),
            check_out_date=self.ci + timedelta(days=3),
            nights=2, guest_name="Existing", nightly_rate=Decimal("200"),
            total_amount=Decimal("400"),
        )
        result = AvailabilityService.check_availability(self.prop.id, self.ci, self.co)
        self.assertFalse(result["available"])

    def test_blocked_by_calendar_block(self):
        CalendarBlock.objects.create(
            property=self.prop, start_date=self.ci, end_date=self.co,
            block_type="owner_block",
        )
        result = AvailabilityService.check_availability(self.prop.id, self.ci, self.co)
        self.assertFalse(result["available"])

    def test_inactive_property(self):
        self.prop.status = "inactive"
        self.prop.save()
        result = AvailabilityService.check_availability(self.prop.id, self.ci, self.co)
        self.assertFalse(result["available"])

    def test_direct_booking_disabled(self):
        self.prop.is_direct_booking_enabled = False
        self.prop.save()
        result = AvailabilityService.check_availability(self.prop.id, self.ci, self.co)
        self.assertFalse(result["available"])

    def test_below_min_nights(self):
        co = self.ci + timedelta(days=1)
        result = AvailabilityService.check_availability(self.prop.id, self.ci, co)
        self.assertFalse(result["available"])
        self.assertIn("Minimum", result["reason"])

    def test_above_max_nights(self):
        co = self.ci + timedelta(days=31)
        result = AvailabilityService.check_availability(self.prop.id, self.ci, co)
        self.assertFalse(result["available"])

    def test_past_date(self):
        ci = date.today() - timedelta(days=1)
        co = date.today() + timedelta(days=2)
        result = AvailabilityService.check_availability(self.prop.id, ci, co)
        self.assertFalse(result["available"])

    def test_non_overlapping_reservation(self):
        Reservation.objects.create(
            property=self.prop, channel="airbnb", status="confirmed",
            confirmation_code="AIR-002",
            check_in_date=self.co + timedelta(days=1),
            check_out_date=self.co + timedelta(days=3),
            nights=2, guest_name="Later", nightly_rate=Decimal("200"),
            total_amount=Decimal("400"),
        )
        result = AvailabilityService.check_availability(self.prop.id, self.ci, self.co)
        self.assertTrue(result["available"])


class TestGetAvailableDates(TestCase):
    def setUp(self):
        self.prop = _create_property()

    def test_returns_month_days(self):
        result = AvailabilityService.get_available_dates(self.prop.id, 7, 2025)
        self.assertEqual(len(result), 31)  # July

    def test_marks_booked_dates(self):
        # Use a future month that is definitely after today
        future_year = date.today().year + 1
        Reservation.objects.create(
            property=self.prop, channel="direct", status="confirmed",
            confirmation_code="WS-001",
            check_in_date=date(future_year, 6, 10),
            check_out_date=date(future_year, 6, 15),
            nights=5, guest_name="Test", nightly_rate=Decimal("200"),
            total_amount=Decimal("1000"),
        )
        result = AvailabilityService.get_available_dates(self.prop.id, 6, future_year)
        by_date = {r["date"]: r for r in result}
        self.assertFalse(by_date[f"{future_year}-06-12"]["available"])
        self.assertTrue(by_date[f"{future_year}-06-20"]["available"])
