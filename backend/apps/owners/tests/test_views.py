from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.payments.models import OwnerPayout
from apps.properties.models import Property
from apps.reservations.models import Reservation


def _create_owner(username="owner", email="owner@test.com"):
    return User.objects.create_user(username=username, email=email, password="t", role="owner")


def _create_property(owner, name="Beach House"):
    return Property.objects.create(
        owner=owner, name=name, slug=name.lower().replace(" ", "-"),
        property_type="house", address="123 St", city="Miami",
        state="FL", zip_code="33139", status="active",
        base_nightly_rate=Decimal("200"),
    )


class TestOwnerDashboardView(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.prop = _create_property(self.owner)
        self.api = APIClient()
        self.api.force_authenticate(user=self.owner)

    def test_returns_dashboard(self):
        response = self.api.get("/api/v1/owners/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("properties_count", response.data)
        self.assertIn("revenue", response.data)
        self.assertIn("occupancy", response.data)

    def test_guest_rejected(self):
        guest = User.objects.create_user(username="g", email="g@t.com", password="t", role="guest")
        self.api.force_authenticate(user=guest)
        response = self.api.get("/api/v1/owners/dashboard/")
        self.assertEqual(response.status_code, 403)


class TestOwnerPropertiesList(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        _create_property(self.owner, "Prop 1")
        _create_property(self.owner, "Prop 2")
        self.api = APIClient()
        self.api.force_authenticate(user=self.owner)

    def test_lists_own_properties(self):
        response = self.api.get("/api/v1/owners/properties/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_other_owner_sees_own(self):
        other = _create_owner("other", "other@t.com")
        _create_property(other, "Other Prop")
        self.api.force_authenticate(user=other)
        response = self.api.get("/api/v1/owners/properties/")
        self.assertEqual(response.data["count"], 1)

    def test_includes_annotated_counts(self):
        response = self.api.get("/api/v1/owners/properties/")
        for prop in response.data["results"]:
            self.assertIn("active_reservations_count", prop)
            self.assertIn("devices_count", prop)


class TestOwnerPropertyDetail(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.prop = _create_property(self.owner)
        self.api = APIClient()
        self.api.force_authenticate(user=self.owner)

    def test_returns_detail(self):
        response = self.api.get(f"/api/v1/owners/properties/{self.prop.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Beach House")
        # Should NOT expose internal fields
        self.assertNotIn("hostaway_raw_data", response.data)
        self.assertNotIn("hostaway_listing_id", response.data)

    def test_other_owner_gets_404(self):
        other = _create_owner("other", "other@t.com")
        self.api.force_authenticate(user=other)
        response = self.api.get(f"/api/v1/owners/properties/{self.prop.id}/")
        self.assertEqual(response.status_code, 404)


class TestOwnerReservations(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.prop = _create_property(self.owner)
        Reservation.objects.create(
            property=self.prop, channel="direct", status="confirmed",
            confirmation_code="WS-001",
            check_in_date=date.today() + timedelta(days=5),
            check_out_date=date.today() + timedelta(days=10),
            nights=5, guest_name="Guest 1",
            nightly_rate=Decimal("200"), total_amount=Decimal("1000"),
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.owner)

    def test_lists_own_reservations(self):
        response = self.api.get("/api/v1/owners/reservations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_isolation_from_other_owner(self):
        other = _create_owner("other", "other@t.com")
        self.api.force_authenticate(user=other)
        response = self.api.get("/api/v1/owners/reservations/")
        self.assertEqual(response.data["count"], 0)


class TestRevenueReport(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.prop = _create_property(self.owner)
        Reservation.objects.create(
            property=self.prop, channel="direct", status="checked_out",
            confirmation_code="WS-REV1",
            check_in_date=date.today() - timedelta(days=10),
            check_out_date=date.today() - timedelta(days=5),
            nights=5, guest_name="Guest",
            nightly_rate=Decimal("200"), total_amount=Decimal("1000"),
            checked_out_at=timezone.now(),
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.owner)

    def test_returns_report(self):
        response = self.api.get(f"/api/v1/owners/revenue/?year={date.today().year}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("properties", response.data)
        self.assertIn("totals", response.data)
        self.assertEqual(response.data["totals"]["gross_revenue"], 1000.0)


class TestOwnerProfile(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.api = APIClient()
        self.api.force_authenticate(user=self.owner)

    def test_get_profile(self):
        response = self.api.get("/api/v1/owners/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "owner@test.com")
        self.assertIn("commission_rate", response.data)
        self.assertIn("stripe_connected", response.data)

    def test_update_company_name(self):
        response = self.api.put("/api/v1/owners/profile/", {"company_name": "My LLC"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["company_name"], "My LLC")

    def test_cannot_update_commission_rate(self):
        """commission_rate is read-only for owners."""
        response = self.api.put("/api/v1/owners/profile/", {
            "company_name": "LLC", "commission_rate": "0.100",
        })
        self.owner.owner_profile.refresh_from_db()
        self.assertEqual(self.owner.owner_profile.commission_rate, Decimal("0.200"))


class TestOwnerPayouts(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        OwnerPayout.objects.create(
            owner=self.owner, period_month=5, period_year=2025,
            gross_revenue=Decimal("5000"), commission_amount=Decimal("1000"),
            net_amount=Decimal("4000"), commission_rate_applied=Decimal("0.200"),
            status="paid",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.owner)

    def test_lists_payouts(self):
        response = self.api.get("/api/v1/owners/payouts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_isolation(self):
        other = _create_owner("other", "other@t.com")
        self.api.force_authenticate(user=other)
        response = self.api.get("/api/v1/owners/payouts/")
        self.assertEqual(response.data["count"], 0)
