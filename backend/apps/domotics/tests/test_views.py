from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.domotics.models import LockAccessCode, NoiseAlert, SmartDevice
from apps.properties.models import Property
from apps.reservations.models import Reservation


def _setup_property_with_devices():
    owner = User.objects.create_user(
        username="owner", email="owner@test.com", password="test", role="owner",
    )
    prop = Property.objects.create(
        owner=owner, name="Test Villa", slug="test-villa",
        property_type="villa", address="123 St", city="Miami",
        state="FL", zip_code="33139", base_nightly_rate=Decimal("300.00"),
        check_in_time=time(16, 0), check_out_time=time(11, 0),
    )
    lock = SmartDevice.objects.create(
        property=prop, device_type="smart_lock", brand="august",
        external_device_id="seam_lock_1", display_name="Front Door", status="online",
    )
    return owner, prop, lock


class TestGuestAccessInfoView(TestCase):
    def setUp(self):
        self.owner, self.prop, self.lock = _setup_property_with_devices()
        self.guest = User.objects.create_user(
            username="guest", email="guest@test.com", password="test", role="guest",
        )
        self.reservation = Reservation.objects.create(
            property=self.prop, guest_user=self.guest,
            channel="direct", status="confirmed",
            confirmation_code="WS-001",
            check_in_date=date.today() + timedelta(days=1),
            check_out_date=date.today() + timedelta(days=5),
            nights=4, guest_name="Test Guest",
            nightly_rate=Decimal("300.00"), total_amount=Decimal("1200.00"),
        )
        self.code = LockAccessCode.objects.create(
            device=self.lock, reservation=self.reservation,
            code="847291", code_name="WS-001 Front Door",
            status="active",
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=4),
        )
        self.api = APIClient()

    def test_guest_sees_full_code(self):
        self.api.force_authenticate(user=self.guest)
        response = self.api.get(f"/api/v1/domotics/reservations/{self.reservation.id}/access/")

        self.assertEqual(response.status_code, 200)
        codes = response.data["access_codes"]
        self.assertEqual(len(codes), 1)
        self.assertEqual(codes[0]["code"], "847291")  # Full code visible

    def test_other_guest_cannot_see(self):
        other = User.objects.create_user(
            username="other", email="other@test.com", password="test", role="guest",
        )
        self.api.force_authenticate(user=other)
        response = self.api.get(f"/api/v1/domotics/reservations/{self.reservation.id}/access/")
        self.assertEqual(response.status_code, 404)

    def test_rejects_too_early(self):
        self.reservation.check_in_date = date.today() + timedelta(days=10)
        self.reservation.save()

        self.api.force_authenticate(user=self.guest)
        response = self.api.get(f"/api/v1/domotics/reservations/{self.reservation.id}/access/")
        self.assertEqual(response.status_code, 403)

    def test_rejects_cancelled_reservation(self):
        self.reservation.status = "cancelled"
        self.reservation.save()

        self.api.force_authenticate(user=self.guest)
        response = self.api.get(f"/api/v1/domotics/reservations/{self.reservation.id}/access/")
        self.assertEqual(response.status_code, 403)


class TestOwnerAccessCodes(TestCase):
    def setUp(self):
        self.owner, self.prop, self.lock = _setup_property_with_devices()
        guest = User.objects.create_user(
            username="guest", email="guest@test.com", password="test", role="guest",
        )
        self.reservation = Reservation.objects.create(
            property=self.prop, guest_user=guest,
            channel="direct", status="confirmed",
            confirmation_code="WS-001",
            check_in_date=date.today(), check_out_date=date.today() + timedelta(days=3),
            nights=3, guest_name="Test",
            nightly_rate=Decimal("300.00"), total_amount=Decimal("900.00"),
        )
        LockAccessCode.objects.create(
            device=self.lock, reservation=self.reservation,
            code="847291", code_name="WS-001 Front Door",
            status="active",
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=3),
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.owner)

    def test_owner_sees_masked_code(self):
        response = self.api.get(f"/api/v1/domotics/properties/{self.prop.id}/access-codes/")

        self.assertEqual(response.status_code, 200)
        codes = response.data["results"]
        self.assertEqual(len(codes), 1)
        self.assertEqual(codes[0]["masked_code"], "****91")
        self.assertNotIn("code", codes[0])  # full code NOT present


class TestSeamWebhookView(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.url = "/api/v1/domotics/webhooks/seam/"

    @patch("apps.domotics.views.process_seam_webhook_event.delay")
    def test_accepts_valid_webhook(self, mock_task):
        response = self.api.post(self.url, {
            "event_type": "device.connected",
            "device_id": "seam_123",
        }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "accepted")
        mock_task.assert_called_once()

    @patch("apps.domotics.views.process_seam_webhook_event.delay")
    def test_ignores_empty_event(self, mock_task):
        response = self.api.post(self.url, {"data": {}}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ignored")
        mock_task.assert_not_called()

    def test_rejects_non_dict(self):
        response = self.api.post(self.url, "not json", content_type="text/plain")
        self.assertIn(response.status_code, (400, 415))


class TestNoiseAlertsView(TestCase):
    def setUp(self):
        self.owner, self.prop, _ = _setup_property_with_devices()
        sensor = SmartDevice.objects.create(
            property=self.prop, device_type="noise_sensor", brand="minut",
            external_device_id="seam_noise_1", display_name="Sensor", status="online",
        )
        NoiseAlert.objects.create(
            device=sensor, decibel_level=Decimal("78.5"),
            threshold_exceeded=True, severity="warning",
        )
        NoiseAlert.objects.create(
            device=sensor, decibel_level=Decimal("92.0"),
            threshold_exceeded=True, severity="critical",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.owner)

    def test_lists_alerts(self):
        response = self.api.get(f"/api/v1/domotics/properties/{self.prop.id}/noise-alerts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_filters_by_severity(self):
        response = self.api.get(
            f"/api/v1/domotics/properties/{self.prop.id}/noise-alerts/?severity=critical"
        )
        self.assertEqual(response.data["count"], 1)
