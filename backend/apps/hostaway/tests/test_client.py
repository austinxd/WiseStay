import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.hostaway.client import HostawayAPIClient
from apps.hostaway.exceptions import (
    HostawayAPIError,
    HostawayAuthError,
    HostawayRateLimitError,
)
from apps.hostaway.models import HostawayCredential
from common.utils.encryption import encrypt


@override_settings(HOSTAWAY_API_URL="https://api.hostaway.com/v1")
class TestHostawayAPIClient(TestCase):
    def setUp(self):
        self.cred = HostawayCredential.objects.create(
            client_id="test_client",
            client_secret=encrypt("test_secret"),
            access_token=encrypt("valid_token_123"),
            token_expires_at=timezone.now() + timedelta(hours=24),
            is_active=True,
        )
        self.client = HostawayAPIClient()

    def tearDown(self):
        self.client.close()

    def _mock_response(self, status_code=200, json_data=None, headers=None):
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = json_data or {"status": "success", "result": []}
        mock.text = json.dumps(json_data or {})
        mock.headers = headers or {}
        return mock

    @patch.object(HostawayAPIClient, "_throttle")
    def test_get_listings_success(self, mock_throttle):
        listings = [{"id": 1, "name": "Test"}]
        mock_resp = self._mock_response(json_data={"status": "success", "result": listings})

        with patch.object(self.client._http, "request", return_value=mock_resp) as mock_req:
            result = self.client.get_listings(limit=50, offset=0)

        self.assertEqual(result, listings)
        mock_req.assert_called_once()
        args, kwargs = mock_req.call_args
        self.assertEqual(args[0], "GET")
        self.assertIn("listings", args[1])

    @patch.object(HostawayAPIClient, "_throttle")
    def test_get_reservation_success(self, mock_throttle):
        res = {"id": 54321, "guestName": "Test Guest"}
        mock_resp = self._mock_response(json_data={"status": "success", "result": res})

        with patch.object(self.client._http, "request", return_value=mock_resp):
            result = self.client.get_reservation(54321)

        self.assertEqual(result["id"], 54321)

    @patch.object(HostawayAPIClient, "_throttle")
    def test_create_reservation_success(self, mock_throttle):
        created = {"id": 99999, "status": "confirmed"}
        mock_resp = self._mock_response(json_data={"status": "success", "result": created})

        with patch.object(self.client._http, "request", return_value=mock_resp):
            result = self.client.create_reservation({"listingMapId": 1})

        self.assertEqual(result["id"], 99999)

    @patch.object(HostawayAPIClient, "_throttle")
    def test_api_failure_raises_error(self, mock_throttle):
        mock_resp = self._mock_response(
            json_data={"status": "fail", "result": "Invalid listing ID"}
        )

        with patch.object(self.client._http, "request", return_value=mock_resp):
            with self.assertRaises(HostawayAPIError) as ctx:
                self.client.get_listing(99999)

        self.assertIn("Invalid listing ID", str(ctx.exception))

    @patch.object(HostawayAPIClient, "_throttle")
    def test_http_500_raises_error(self, mock_throttle):
        mock_resp = self._mock_response(status_code=500, json_data={})

        with patch.object(self.client._http, "request", return_value=mock_resp):
            with self.assertRaises(HostawayAPIError) as ctx:
                self.client.get_listings()

        self.assertEqual(ctx.exception.status_code, 500)

    @patch.object(HostawayAPIClient, "_throttle")
    @patch.object(HostawayAPIClient, "_refresh_token", return_value="new_token")
    def test_auth_error_refreshes_token(self, mock_refresh, mock_throttle):
        # First call returns 403, second succeeds
        mock_403 = self._mock_response(status_code=403)
        mock_ok = self._mock_response(json_data={"status": "success", "result": []})

        with patch.object(self.client._http, "request", side_effect=[mock_403, mock_ok]):
            result = self.client.get_listings()

        self.assertEqual(result, [])
        mock_refresh.assert_called_once()

    @patch.object(HostawayAPIClient, "_throttle")
    @patch("time.sleep")
    def test_rate_limit_retries(self, mock_sleep, mock_throttle):
        mock_429 = self._mock_response(status_code=429, headers={"Retry-After": "2"})
        mock_ok = self._mock_response(json_data={"status": "success", "result": []})

        with patch.object(self.client._http, "request", side_effect=[mock_429, mock_ok]):
            result = self.client.get_listings()

        self.assertEqual(result, [])
        mock_sleep.assert_called()

    @patch.object(HostawayAPIClient, "_throttle")
    @patch("time.sleep")
    def test_rate_limit_exhausted_raises(self, mock_sleep, mock_throttle):
        mock_429 = self._mock_response(status_code=429, headers={"Retry-After": "1"})

        with patch.object(self.client._http, "request", return_value=mock_429):
            with self.assertRaises(HostawayRateLimitError):
                self.client.get_listings()

    def test_get_token_from_credential(self):
        token = self.client._get_token()
        self.assertEqual(token, "valid_token_123")

    def test_get_token_no_credential_raises(self):
        HostawayCredential.objects.all().delete()
        with self.assertRaises(HostawayAuthError):
            self.client._get_token()

    def test_get_token_expired_refreshes(self):
        self.cred.token_expires_at = timezone.now() - timedelta(hours=1)
        self.cred.save()

        with patch.object(self.client, "_refresh_token", return_value="new_token") as mock:
            token = self.client._get_token()

        self.assertEqual(token, "new_token")
        mock.assert_called_once()

    @patch.object(HostawayAPIClient, "_throttle")
    def test_get_calendar(self, mock_throttle):
        cal = [{"date": "2025-07-10", "isAvailable": 1}]
        mock_resp = self._mock_response(json_data={"status": "success", "result": cal})

        with patch.object(self.client._http, "request", return_value=mock_resp):
            result = self.client.get_calendar(98765, "2025-07-10", "2025-07-25")

        self.assertEqual(result, cal)

    @patch.object(HostawayAPIClient, "_throttle")
    def test_send_message(self, mock_throttle):
        msg = {"id": 1, "body": "Hello"}
        mock_resp = self._mock_response(json_data={"status": "success", "result": msg})

        with patch.object(self.client._http, "request", return_value=mock_resp):
            result = self.client.send_message(100, "Hello")

        self.assertEqual(result["body"], "Hello")
