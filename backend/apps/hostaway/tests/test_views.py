import base64
import json
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.hostaway.models import HostawayCredential, SyncLog

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestWebhookEndpoint(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.url = "/api/v1/hostaway/webhooks/unified/"
        self.cred = HostawayCredential.objects.create(
            client_id="test", client_secret="secret", is_active=True,
        )

    @patch("apps.hostaway.views.process_webhook_event.delay")
    def test_accepts_valid_webhook(self, mock_task):
        with open(FIXTURES_DIR / "webhook_reservation_created.json") as f:
            payload = json.load(f)

        response = self.api.post(self.url, data=payload, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "accepted")
        mock_task.assert_called_once()

    @patch("apps.hostaway.views.process_webhook_event.delay")
    def test_returns_200_for_unknown_event(self, mock_task):
        response = self.api.post(
            self.url, data={"event": "unknownEvent", "data": {}}, format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ignored")
        mock_task.assert_not_called()

    def test_rejects_invalid_payload(self):
        response = self.api.post(
            self.url, data="not json", content_type="text/plain",
        )
        self.assertIn(response.status_code, (400, 415))

    @patch("apps.hostaway.views.process_webhook_event.delay")
    def test_basic_auth_validation(self, mock_task):
        self.cred.webhook_secret = "admin:secretpass"
        self.cred.save()

        # No auth → rejected
        response = self.api.post(
            self.url,
            data={"event": "reservationCreated", "data": {"id": 1}},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

        # Wrong auth → rejected
        bad_creds = base64.b64encode(b"admin:wrong").decode()
        response = self.api.post(
            self.url,
            data={"event": "reservationCreated", "data": {"id": 1}},
            format="json",
            HTTP_AUTHORIZATION=f"Basic {bad_creds}",
        )
        self.assertEqual(response.status_code, 401)

        # Correct auth → accepted
        good_creds = base64.b64encode(b"admin:secretpass").decode()
        response = self.api.post(
            self.url,
            data={"event": "reservationCreated", "data": {"id": 1}},
            format="json",
            HTTP_AUTHORIZATION=f"Basic {good_creds}",
        )
        self.assertEqual(response.status_code, 200)


class TestManualSyncEndpoints(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

    @patch("apps.hostaway.views.sync_listings_task.delay")
    def test_trigger_listings_sync(self, mock_task):
        response = self.api.post("/api/v1/hostaway/sync/listings/")
        self.assertEqual(response.status_code, 202)
        mock_task.assert_called_once()

    @patch("apps.hostaway.views.sync_reservations_task.delay")
    def test_trigger_reservations_sync(self, mock_task):
        response = self.api.post("/api/v1/hostaway/sync/reservations/")
        self.assertEqual(response.status_code, 202)
        mock_task.assert_called_once()

    @patch("apps.hostaway.views.sync_calendar_task.delay")
    def test_trigger_calendar_sync(self, mock_task):
        response = self.api.post("/api/v1/hostaway/sync/calendar/")
        self.assertEqual(response.status_code, 202)
        mock_task.assert_called_once()

    def test_sync_logs_list(self):
        SyncLog.objects.create(sync_type="listings", status="success", triggered_by="test")
        SyncLog.objects.create(sync_type="reservations", status="failed", triggered_by="test")

        response = self.api.get("/api/v1/hostaway/sync/logs/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_non_admin_rejected(self):
        guest = User.objects.create_user(
            username="guest", email="g@test.com", password="test", role="guest",
        )
        self.api.force_authenticate(user=guest)

        response = self.api.post("/api/v1/hostaway/sync/listings/")
        self.assertEqual(response.status_code, 403)
