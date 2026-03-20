import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.domotics.models import NoiseAlert, SmartDevice
from apps.payments.models import OwnerPayout
from apps.properties.models import CalendarBlock, Property
from apps.reservations.models import Reservation


def _create_owner(username="owner1", email="owner1@test.com"):
    return User.objects.create_user(username=username, email=email, password="t", role="owner")


def _create_property(owner, name="Beach House", slug=None):
    slug = slug or name.lower().replace(" ", "-")
    return Property.objects.create(
        owner=owner, name=name, slug=slug, property_type="house",
        address="123 St", city="Miami", state="FL", zip_code="33139",
        status="active", base_nightly_rate=Decimal("200"),
        cleaning_fee=Decimal("100"),
    )


def _create_reservation(prop, channel="direct", status="checked_out", total=Decimal("800"), **kw):
    defaults = {
        "property": prop, "channel": channel, "status": status,
        "confirmation_code": f"WS-{Reservation.objects.count() + 1:06d}",
        "check_in_date": date.today() - timedelta(days=10),
        "check_out_date": date.today() - timedelta(days=5),
        "nights": 5, "guest_name": "Test Guest",
        "nightly_rate": Decimal("160"), "total_amount": total,
    }
    if status == "checked_out":
        defaults["checked_out_at"] = timezone.now()
    defaults.update(kw)
    return Reservation.objects.create(**defaults)


class TestDashboardSummary(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.prop = _create_property(self.owner)

    def test_returns_properties_count(self):
        from apps.owners.services import OwnerDashboardService

        result = OwnerDashboardService.get_dashboard_summary(self.owner.id)
        self.assertEqual(result["properties_count"], 1)
        self.assertEqual(result["active_properties"], 1)

    def test_revenue_ytd(self):
        from apps.owners.services import OwnerDashboardService

        _create_reservation(self.prop, total=Decimal("1000"))
        _create_reservation(self.prop, total=Decimal("500"))

        result = OwnerDashboardService.get_dashboard_summary(self.owner.id)
        self.assertEqual(result["revenue"]["ytd"], 1500.0)

    def test_channel_breakdown(self):
        from apps.owners.services import OwnerDashboardService

        _create_reservation(self.prop, channel="direct", total=Decimal("500"))
        _create_reservation(self.prop, channel="airbnb", total=Decimal("700"))
        _create_reservation(self.prop, channel="airbnb", total=Decimal("300"))

        result = OwnerDashboardService.get_dashboard_summary(self.owner.id)
        breakdown = result["channel_breakdown_ytd"]
        self.assertEqual(breakdown["direct"]["count"], 1)
        self.assertEqual(breakdown["airbnb"]["count"], 2)
        self.assertEqual(breakdown["airbnb"]["revenue"], 1000.0)

    def test_upcoming_reservations(self):
        from apps.owners.services import OwnerDashboardService

        _create_reservation(
            self.prop, status="confirmed",
            check_in_date=date.today() + timedelta(days=5),
            check_out_date=date.today() + timedelta(days=10),
        )
        result = OwnerDashboardService.get_dashboard_summary(self.owner.id)
        self.assertEqual(result["upcoming_reservations"], 1)

    def test_active_guests(self):
        from apps.owners.services import OwnerDashboardService

        _create_reservation(self.prop, status="checked_in")
        result = OwnerDashboardService.get_dashboard_summary(self.owner.id)
        self.assertEqual(result["active_guests_now"], 1)

    def test_alerts_offline_device(self):
        from apps.owners.services import OwnerDashboardService

        SmartDevice.objects.create(
            property=self.prop, device_type="smart_lock", brand="august",
            external_device_id="s1", display_name="Front Door", status="offline",
        )
        result = OwnerDashboardService.get_dashboard_summary(self.owner.id)
        self.assertTrue(any(a["type"] == "device_offline" for a in result["alerts"]))

    def test_alerts_low_battery(self):
        from apps.owners.services import OwnerDashboardService

        SmartDevice.objects.create(
            property=self.prop, device_type="thermostat", brand="nest",
            external_device_id="s2", display_name="Thermostat", status="online",
            battery_level=12,
        )
        result = OwnerDashboardService.get_dashboard_summary(self.owner.id)
        self.assertTrue(any(a["type"] == "low_battery" for a in result["alerts"]))

    def test_alerts_noise(self):
        from apps.owners.services import OwnerDashboardService

        sensor = SmartDevice.objects.create(
            property=self.prop, device_type="noise_sensor", brand="minut",
            external_device_id="s3", display_name="Sensor", status="online",
        )
        NoiseAlert.objects.create(
            device=sensor, decibel_level=Decimal("82"), severity="critical",
            threshold_exceeded=True,
        )
        result = OwnerDashboardService.get_dashboard_summary(self.owner.id)
        self.assertTrue(any(a["type"] == "noise_alert" for a in result["alerts"]))


class TestPropertyPerformance(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.prop = _create_property(self.owner)

    def test_returns_revenue_data(self):
        from apps.owners.services import OwnerDashboardService

        _create_reservation(self.prop, total=Decimal("1000"))
        result = OwnerDashboardService.get_property_performance(
            self.prop.id, self.owner.id,
        )
        self.assertEqual(result["property"]["name"], "Beach House")
        self.assertEqual(result["revenue"]["total"], 1000.0)
        self.assertEqual(result["revenue"]["commission"], 200.0)  # 20%
        self.assertEqual(result["revenue"]["net_to_owner"], 800.0)

    def test_rejects_other_owner(self):
        from apps.owners.services import OwnerDashboardService

        other = _create_owner("other", "other@test.com")
        with self.assertRaises(Property.DoesNotExist):
            OwnerDashboardService.get_property_performance(self.prop.id, other.id)


class TestRevenueReport(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.prop1 = _create_property(self.owner, "Beach House", "beach")
        self.prop2 = _create_property(self.owner, "Mountain Cabin", "mountain")

    def test_multi_property_report(self):
        from apps.owners.services import OwnerDashboardService

        _create_reservation(self.prop1, total=Decimal("1000"), channel="direct")
        _create_reservation(self.prop2, total=Decimal("600"), channel="airbnb")

        result = OwnerDashboardService.get_revenue_report(
            self.owner.id, date.today().year,
        )
        self.assertEqual(len(result["properties"]), 2)
        self.assertEqual(result["totals"]["gross_revenue"], 1600.0)
        self.assertEqual(result["totals"]["total_reservations"], 2)


class TestOccupancyCalendar(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.prop = _create_property(self.owner)

    def test_shows_booked_dates(self):
        from apps.owners.services import OwnerDashboardService

        future_year = date.today().year + 1
        _create_reservation(
            self.prop, status="confirmed",
            check_in_date=date(future_year, 6, 10),
            check_out_date=date(future_year, 6, 15),
        )

        result = OwnerDashboardService.get_occupancy_calendar(
            self.prop.id, self.owner.id, 6, future_year,
        )
        self.assertEqual(len(result), 30)  # June has 30 days
        by_date = {r["date"]: r for r in result}
        self.assertEqual(by_date[f"{future_year}-06-12"]["status"], "booked")
        self.assertEqual(by_date[f"{future_year}-06-20"]["status"], "available")

    def test_shows_blocked_dates(self):
        from apps.owners.services import OwnerDashboardService

        future_year = date.today().year + 1
        CalendarBlock.objects.create(
            property=self.prop,
            start_date=date(future_year, 6, 5),
            end_date=date(future_year, 6, 8),
            block_type="owner_block",
            reason="Personal use",
        )

        result = OwnerDashboardService.get_occupancy_calendar(
            self.prop.id, self.owner.id, 6, future_year,
        )
        by_date = {r["date"]: r for r in result}
        self.assertEqual(by_date[f"{future_year}-06-06"]["status"], "blocked")

    def test_rejects_other_owner(self):
        from apps.owners.services import OwnerDashboardService

        other = _create_owner("other", "other@test.com")
        with self.assertRaises(Property.DoesNotExist):
            OwnerDashboardService.get_occupancy_calendar(
                self.prop.id, other.id, 6, 2025,
            )


class TestOwnerIsolation(TestCase):
    """Critical: Owner A cannot see Owner B's data."""

    def setUp(self):
        self.owner_a = _create_owner("ownerA", "a@test.com")
        self.owner_b = _create_owner("ownerB", "b@test.com")
        self.prop_a = _create_property(self.owner_a, "Prop A", "prop-a")
        self.prop_b = _create_property(self.owner_b, "Prop B", "prop-b")
        _create_reservation(self.prop_a, total=Decimal("1000"))
        _create_reservation(self.prop_b, total=Decimal("2000"))

    def test_dashboard_only_shows_own_data(self):
        from apps.owners.services import OwnerDashboardService

        result_a = OwnerDashboardService.get_dashboard_summary(self.owner_a.id)
        result_b = OwnerDashboardService.get_dashboard_summary(self.owner_b.id)

        self.assertEqual(result_a["revenue"]["ytd"], 1000.0)
        self.assertEqual(result_b["revenue"]["ytd"], 2000.0)
        self.assertEqual(result_a["properties_count"], 1)
        self.assertEqual(result_b["properties_count"], 1)

    def test_reservations_isolated(self):
        from apps.owners.services import OwnerDashboardService

        res_a = OwnerDashboardService.get_reservations_for_owner(self.owner_a.id)
        res_b = OwnerDashboardService.get_reservations_for_owner(self.owner_b.id)

        self.assertEqual(res_a.count(), 1)
        self.assertEqual(res_b.count(), 1)
        self.assertNotEqual(
            res_a.first().property_id,
            res_b.first().property_id,
        )

    def test_revenue_report_isolated(self):
        from apps.owners.services import OwnerDashboardService

        rep_a = OwnerDashboardService.get_revenue_report(self.owner_a.id, date.today().year)
        rep_b = OwnerDashboardService.get_revenue_report(self.owner_b.id, date.today().year)

        self.assertEqual(rep_a["totals"]["gross_revenue"], 1000.0)
        self.assertEqual(rep_b["totals"]["gross_revenue"], 2000.0)
