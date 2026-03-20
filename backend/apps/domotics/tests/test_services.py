from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import GuestProfile, User
from apps.domotics.models import (
    LockAccessCode,
    NoiseAlert,
    SmartDevice,
    ThermostatLog,
)
from apps.domotics.services import (
    TRIVIAL_CODES,
    DomoticsOrchestrator,
    _generate_code,
)
from apps.properties.models import Property
from apps.reservations.models import Reservation


def _create_owner():
    return User.objects.create_user(
        username="owner", email="owner@test.com", password="test", role="owner",
    )


def _create_guest(username="guest1", email="guest@test.com"):
    return User.objects.create_user(
        username=username, email=email, password="test", role="guest",
    )


def _create_property(owner):
    return Property.objects.create(
        owner=owner, name="Beach House", slug="beach-house",
        property_type="house", address="123 Ocean Dr", city="Miami",
        state="FL", zip_code="33139",
        base_nightly_rate=Decimal("300.00"),
        check_in_time=time(16, 0), check_out_time=time(11, 0),
    )


def _create_lock(prop, name="Front Door Lock", brand="august"):
    return SmartDevice.objects.create(
        property=prop, device_type="smart_lock", brand=brand,
        external_device_id=f"seam_{prop.id}_{name.replace(' ', '_').lower()}",
        display_name=name, status="online",
    )


def _create_thermostat(prop, name="Living Room Thermostat"):
    return SmartDevice.objects.create(
        property=prop, device_type="thermostat", brand="nest",
        external_device_id=f"seam_therm_{prop.id}",
        display_name=name, status="online",
    )


def _create_noise_sensor(prop, name="Bedroom Sensor"):
    return SmartDevice.objects.create(
        property=prop, device_type="noise_sensor", brand="minut",
        external_device_id=f"seam_noise_{prop.id}",
        display_name=name, status="online",
        config={"noise_threshold_db": 70},
    )


def _create_reservation(prop, guest, **kwargs):
    defaults = {
        "property": prop, "guest_user": guest,
        "channel": "direct", "status": "confirmed",
        "confirmation_code": f"WS-{Reservation.objects.count() + 1:06d}",
        "check_in_date": date.today() + timedelta(days=1),
        "check_out_date": date.today() + timedelta(days=5),
        "nights": 4, "guest_name": "Test Guest",
        "nightly_rate": Decimal("300.00"), "total_amount": Decimal("1200.00"),
    }
    defaults.update(kwargs)
    return Reservation.objects.create(**defaults)


class TestGenerateCode(TestCase):
    def test_generates_6_digit_code(self):
        code = _generate_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_excludes_trivial_codes(self):
        codes = {_generate_code() for _ in range(200)}
        for trivial in TRIVIAL_CODES:
            self.assertNotIn(trivial, codes)

    def test_respects_custom_length(self):
        code = _generate_code(length=8)
        self.assertEqual(len(code), 8)


class TestGenerateAccessCode(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.guest = _create_guest()
        self.prop = _create_property(self.owner)
        self.lock = _create_lock(self.prop)
        self.reservation = _create_reservation(self.prop, self.guest)

    @patch("apps.domotics.services.get_lock_provider")
    def test_creates_code_and_calls_provider(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.create_access_code.return_value = {
            "external_code_id": "ac_123", "status": "set",
        }
        mock_get_provider.return_value = mock_provider

        result = DomoticsOrchestrator.generate_access_code_for_reservation(self.reservation.id)

        self.assertIsNotNone(result)
        self.assertEqual(result.status, "active")
        self.assertIsNotNone(result.activated_at)
        self.assertEqual(len(result.code), 6)
        mock_provider.create_access_code.assert_called_once()

    @patch("apps.domotics.services.get_lock_provider")
    def test_skips_if_code_exists(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.create_access_code.return_value = {"external_code_id": "ac_1", "status": "set"}
        mock_get_provider.return_value = mock_provider

        DomoticsOrchestrator.generate_access_code_for_reservation(self.reservation.id)
        DomoticsOrchestrator.generate_access_code_for_reservation(self.reservation.id)

        self.assertEqual(LockAccessCode.objects.filter(reservation=self.reservation).count(), 1)

    @patch("apps.domotics.services.get_lock_provider")
    def test_handles_provider_failure(self, mock_get_provider):
        from apps.domotics.exceptions import AccessCodeError

        mock_provider = MagicMock()
        mock_provider.create_access_code.side_effect = AccessCodeError("API down")
        mock_get_provider.return_value = mock_provider

        result = DomoticsOrchestrator.generate_access_code_for_reservation(self.reservation.id)

        self.assertIsNotNone(result)
        self.assertEqual(result.status, "failed")
        self.assertIn("API down", result.error_message)
        self.assertEqual(result.retry_count, 1)

    def test_skips_no_locks(self):
        SmartDevice.objects.all().delete()
        result = DomoticsOrchestrator.generate_access_code_for_reservation(self.reservation.id)
        self.assertIsNone(result)

    def test_skips_cancelled_reservation(self):
        self.reservation.status = "cancelled"
        self.reservation.save()
        result = DomoticsOrchestrator.generate_access_code_for_reservation(self.reservation.id)
        self.assertIsNone(result)

    @patch("apps.domotics.services.get_lock_provider")
    def test_generates_for_multiple_locks(self, mock_get_provider):
        _create_lock(self.prop, name="Garage Lock", brand="schlage")
        mock_provider = MagicMock()
        mock_provider.create_access_code.return_value = {"external_code_id": "ac_x", "status": "set"}
        mock_get_provider.return_value = mock_provider

        DomoticsOrchestrator.generate_access_code_for_reservation(self.reservation.id)

        codes = LockAccessCode.objects.filter(reservation=self.reservation)
        self.assertEqual(codes.count(), 2)

    @patch("apps.domotics.services.get_lock_provider")
    def test_valid_from_until_use_property_times(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.create_access_code.return_value = {"external_code_id": "ac_1", "status": "set"}
        mock_get_provider.return_value = mock_provider

        result = DomoticsOrchestrator.generate_access_code_for_reservation(self.reservation.id)

        self.assertEqual(result.valid_from.hour, 16)  # check_in_time
        self.assertEqual(result.valid_until.hour, 11)  # check_out_time


class TestRevokeAccessCode(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.guest = _create_guest()
        self.prop = _create_property(self.owner)
        self.lock = _create_lock(self.prop)
        self.reservation = _create_reservation(self.prop, self.guest)
        self.code = LockAccessCode.objects.create(
            device=self.lock, reservation=self.reservation,
            code="123456", code_name="WS-TEST Front Door Lock",
            status="active",
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=4),
            activated_at=timezone.now(),
        )

    @patch("apps.domotics.services.get_lock_provider")
    def test_revokes_active_codes(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.delete_access_code.return_value = True
        mock_get_provider.return_value = mock_provider

        count = DomoticsOrchestrator.revoke_access_code_for_reservation(self.reservation.id)

        self.assertEqual(count, 1)
        self.code.refresh_from_db()
        self.assertEqual(self.code.status, "revoked")
        self.assertIsNotNone(self.code.revoked_at)

    @patch("apps.domotics.services.get_lock_provider")
    def test_revokes_even_on_provider_failure(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.delete_access_code.side_effect = Exception("API down")
        mock_get_provider.return_value = mock_provider

        count = DomoticsOrchestrator.revoke_access_code_for_reservation(self.reservation.id)

        self.assertEqual(count, 1)
        self.code.refresh_from_db()
        self.assertEqual(self.code.status, "revoked")

    @patch("apps.domotics.services.get_lock_provider")
    def test_revokes_multiple_codes(self, mock_get_provider):
        lock2 = _create_lock(self.prop, "Garage", "schlage")
        LockAccessCode.objects.create(
            device=lock2, reservation=self.reservation,
            code="654321", code_name="WS-TEST Garage",
            status="active",
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=4),
        )
        mock_provider = MagicMock()
        mock_provider.delete_access_code.return_value = True
        mock_get_provider.return_value = mock_provider

        count = DomoticsOrchestrator.revoke_access_code_for_reservation(self.reservation.id)
        self.assertEqual(count, 2)


class TestCheckinTemperature(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.guest = _create_guest()
        self.prop = _create_property(self.owner)
        self.thermostat = _create_thermostat(self.prop)
        self.reservation = _create_reservation(self.prop, self.guest)

    @patch("apps.domotics.services.get_thermostat_provider")
    def test_sets_default_temperature(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.set_temperature.return_value = True
        mock_get_provider.return_value = mock_provider

        result = DomoticsOrchestrator.set_checkin_temperature(self.reservation.id)

        self.assertTrue(result)
        mock_provider.set_temperature.assert_called_once_with(
            device_id=self.thermostat.external_device_id,
            heat_f=68.0, cool_f=72.0,
        )
        self.assertEqual(ThermostatLog.objects.count(), 1)
        log = ThermostatLog.objects.first()
        self.assertEqual(log.event_type, "checkin_preset")
        self.assertEqual(log.triggered_by, "system")

    @patch("apps.domotics.services.get_thermostat_provider")
    def test_uses_guest_cool_preference(self, mock_get_provider):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.preferences = {"temperature_preference": "cool"}
        profile.save()

        mock_provider = MagicMock()
        mock_provider.set_temperature.return_value = True
        mock_get_provider.return_value = mock_provider

        DomoticsOrchestrator.set_checkin_temperature(self.reservation.id)

        mock_provider.set_temperature.assert_called_once_with(
            device_id=self.thermostat.external_device_id,
            heat_f=66.0, cool_f=70.0,
        )

    @patch("apps.domotics.services.get_thermostat_provider")
    def test_uses_guest_warm_preference(self, mock_get_provider):
        profile = GuestProfile.objects.get(user=self.guest)
        profile.preferences = {"temperature_preference": "warm"}
        profile.save()

        mock_provider = MagicMock()
        mock_provider.set_temperature.return_value = True
        mock_get_provider.return_value = mock_provider

        DomoticsOrchestrator.set_checkin_temperature(self.reservation.id)

        mock_provider.set_temperature.assert_called_once_with(
            device_id=self.thermostat.external_device_id,
            heat_f=72.0, cool_f=76.0,
        )

    def test_returns_false_no_thermostats(self):
        SmartDevice.objects.all().delete()
        self.assertFalse(DomoticsOrchestrator.set_checkin_temperature(self.reservation.id))


class TestCheckoutTemperature(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.guest = _create_guest()
        self.prop = _create_property(self.owner)
        self.thermostat = _create_thermostat(self.prop)
        self.reservation = _create_reservation(self.prop, self.guest, status="checked_out")

    @patch("apps.domotics.services.get_thermostat_provider")
    def test_resets_to_eco(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.set_temperature.return_value = True
        mock_provider.set_mode.return_value = True
        mock_get_provider.return_value = mock_provider

        result = DomoticsOrchestrator.reset_checkout_temperature(self.reservation.id)

        self.assertTrue(result)
        mock_provider.set_temperature.assert_called_once_with(
            device_id=self.thermostat.external_device_id,
            heat_f=60.0, cool_f=78.0,
        )
        mock_provider.set_mode.assert_called_once_with(
            self.thermostat.external_device_id, "eco",
        )
        log = ThermostatLog.objects.first()
        self.assertEqual(log.event_type, "checkout_reset")
        self.assertEqual(log.mode, "eco")


class TestProcessNoiseAlert(TestCase):
    def setUp(self):
        self.owner = _create_owner()
        self.guest = _create_guest()
        self.prop = _create_property(self.owner)
        self.sensor = _create_noise_sensor(self.prop)
        self.reservation = _create_reservation(
            self.prop, self.guest, status="checked_in",
            check_in_date=date.today() - timedelta(days=1),
        )

    def test_creates_warning_alert(self):
        alert = DomoticsOrchestrator.process_noise_alert(self.sensor.id, 75.0)

        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, "warning")
        self.assertTrue(alert.threshold_exceeded)
        self.assertEqual(float(alert.decibel_level), 75.0)
        self.assertTrue(alert.alert_sent_to_owner)
        self.assertFalse(alert.alert_sent_to_guest)

    def test_creates_critical_alert_high_db(self):
        alert = DomoticsOrchestrator.process_noise_alert(self.sensor.id, 90.0)
        self.assertEqual(alert.severity, "critical")
        self.assertTrue(alert.alert_sent_to_guest)

    def test_creates_critical_alert_long_duration(self):
        alert = DomoticsOrchestrator.process_noise_alert(self.sensor.id, 75.0, duration_seconds=1000)
        self.assertEqual(alert.severity, "critical")

    def test_ignores_below_threshold(self):
        alert = DomoticsOrchestrator.process_noise_alert(self.sensor.id, 65.0)
        self.assertIsNone(alert)

    def test_associates_active_reservation(self):
        alert = DomoticsOrchestrator.process_noise_alert(self.sensor.id, 80.0)
        self.assertEqual(alert.reservation_id, self.reservation.id)

    def test_handles_unknown_device(self):
        alert = DomoticsOrchestrator.process_noise_alert(99999, 80.0)
        self.assertIsNone(alert)
