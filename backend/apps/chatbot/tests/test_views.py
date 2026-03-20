from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.chatbot.models import Conversation, Message
from apps.loyalty.models import TierConfig
from apps.properties.models import Property
from apps.reservations.models import Reservation


def _setup():
    TierConfig.objects.all().delete()
    TierConfig.objects.create(tier_name="bronze", min_reservations=0, min_referrals=0, discount_percent=0, sort_order=1)
    owner = User.objects.create_user(username="owner", email="o@t.com", password="t", role="owner")
    guest = User.objects.create_user(username="guest", email="g@t.com", password="t", role="guest")
    prop = Property.objects.create(
        owner=owner, name="Villa", slug="villa", property_type="villa",
        address="1 St", city="Miami", state="FL", zip_code="33139",
        base_nightly_rate=Decimal("200"), status="active",
    )
    res = Reservation.objects.create(
        property=prop, guest_user=guest, channel="direct", status="confirmed",
        confirmation_code="WS-VIEW01",
        check_in_date=date.today() + timedelta(days=5),
        check_out_date=date.today() + timedelta(days=10),
        nights=5, guest_name="Test", nightly_rate=Decimal("200"),
        total_amount=Decimal("1000"),
    )
    return guest, owner, prop, res


class TestStartConversation(TestCase):
    def setUp(self):
        self.guest, self.owner, self.prop, self.res = _setup()
        self.api = APIClient()
        self.api.force_authenticate(user=self.guest)

    def test_creates_new_conversation(self):
        response = self.api.post("/api/v1/chatbot/conversations/start/", {
            "reservation_id": self.res.id, "channel": "web",
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["is_new"])
        self.assertIn("conversation_id", response.data)

    def test_returns_existing_conversation(self):
        conv = Conversation.objects.create(
            guest=self.guest, reservation=self.res, channel="web", status="active",
        )
        response = self.api.post("/api/v1/chatbot/conversations/start/", {
            "reservation_id": self.res.id, "channel": "web",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_new"])
        self.assertEqual(response.data["conversation_id"], conv.id)

    def test_non_guest_rejected(self):
        self.api.force_authenticate(user=self.owner)
        response = self.api.post("/api/v1/chatbot/conversations/start/", {})
        self.assertEqual(response.status_code, 403)


class TestConversationList(TestCase):
    def setUp(self):
        self.guest, _, _, self.res = _setup()
        self.api = APIClient()
        self.api.force_authenticate(user=self.guest)
        Conversation.objects.create(guest=self.guest, channel="web")
        Conversation.objects.create(guest=self.guest, reservation=self.res, channel="web")

    def test_lists_guest_conversations(self):
        response = self.api.get("/api/v1/chatbot/conversations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_other_guest_doesnt_see(self):
        other = User.objects.create_user(username="other", email="other@t.com", password="t", role="guest")
        self.api.force_authenticate(user=other)
        response = self.api.get("/api/v1/chatbot/conversations/")
        self.assertEqual(response.data["count"], 0)


class TestSendMessage(TestCase):
    def setUp(self):
        self.guest, _, _, self.res = _setup()
        self.conv = Conversation.objects.create(
            guest=self.guest, reservation=self.res, channel="web",
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.guest)

    @patch("apps.chatbot.ai_service.AIConciergeService.process_message")
    @patch("apps.chatbot.ai_service.AIConciergeService.__init__", return_value=None)
    def test_sends_message_and_gets_response(self, mock_init, mock_process):
        mock_process.return_value = "Hello! How can I help?"

        # Pre-create the AI message that the service would save
        Message.objects.create(
            conversation=self.conv, sender_type="ai",
            content="Hello! How can I help?",
        )

        response = self.api.post(
            f"/api/v1/chatbot/conversations/{self.conv.id}/messages/",
            {"content": "Hi"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["content"], "Hello! How can I help?")

    def test_wrong_conversation_returns_404(self):
        response = self.api.post(
            "/api/v1/chatbot/conversations/99999/messages/",
            {"content": "Hi"},
        )
        self.assertEqual(response.status_code, 404)

    def test_empty_message_rejected(self):
        response = self.api.post(
            f"/api/v1/chatbot/conversations/{self.conv.id}/messages/",
            {"content": ""},
        )
        self.assertEqual(response.status_code, 400)


class TestMessageHistory(TestCase):
    def setUp(self):
        self.guest, _, _, self.res = _setup()
        self.conv = Conversation.objects.create(
            guest=self.guest, reservation=self.res, channel="web",
        )
        Message.objects.create(conversation=self.conv, sender_type="guest", content="Hello")
        Message.objects.create(conversation=self.conv, sender_type="ai", content="Hi there!")
        self.api = APIClient()
        self.api.force_authenticate(user=self.guest)

    def test_returns_messages(self):
        response = self.api.get(f"/api/v1/chatbot/conversations/{self.conv.id}/history/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)


@override_settings(WHATSAPP_VERIFY_TOKEN="test_verify_token")
class TestWhatsAppWebhook(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.url = "/api/v1/chatbot/webhooks/whatsapp/"

    def test_verification_succeeds(self):
        response = self.api.get(self.url, {
            "hub.mode": "subscribe",
            "hub.verify_token": "test_verify_token",
            "hub.challenge": "challenge_123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "challenge_123")

    def test_verification_fails_wrong_token(self):
        response = self.api.get(self.url, {
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "challenge_123",
        })
        self.assertEqual(response.status_code, 403)

    @patch("apps.chatbot.ai_service.AIConciergeService.process_message")
    @patch("apps.chatbot.ai_service.AIConciergeService.__init__", return_value=None)
    @patch("apps.chatbot.whatsapp_service.WhatsAppService.send_message")
    def test_processes_incoming_message(self, mock_wa_send, mock_ai_init, mock_process):
        TierConfig.objects.all().delete()
        TierConfig.objects.create(tier_name="bronze", min_reservations=0, min_referrals=0, discount_percent=0, sort_order=1)
        guest = User.objects.create_user(
            username="waguest", email="wa@t.com", password="t", role="guest",
            phone="+14155551234",
        )

        mock_process.return_value = "Your code is 847291"

        payload = {
            "entry": [{"changes": [{"value": {"messages": [
                {"from": "14155551234", "id": "wamid_123", "type": "text",
                 "text": {"body": "What's my door code?"}, "timestamp": "1234567890"},
            ]}}]}],
        }

        response = self.api.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 200)

        conv = Conversation.objects.filter(guest=guest, channel="whatsapp").first()
        self.assertIsNotNone(conv)

    def test_ignores_unknown_phone(self):
        payload = {
            "entry": [{"changes": [{"value": {"messages": [
                {"from": "19999999999", "id": "wamid_999", "type": "text",
                 "text": {"body": "Hello"}, "timestamp": "1234567890"},
            ]}}]}],
        }

        response = self.api.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_ignores_non_text_messages(self):
        response = self.api.post(self.url, {
            "entry": [{"changes": [{"value": {"messages": [
                {"from": "14155551234", "type": "image"},
            ]}}]}],
        }, format="json")
        self.assertEqual(response.status_code, 200)
