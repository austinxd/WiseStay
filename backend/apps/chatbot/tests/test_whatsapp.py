from django.test import TestCase, override_settings

from apps.chatbot.whatsapp_service import WhatsAppService


class TestParseIncomingMessage(TestCase):
    def test_parses_valid_text_message(self):
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "14155551234",
                            "id": "wamid.abc123",
                            "type": "text",
                            "text": {"body": "What's my door code?"},
                            "timestamp": "1700000000",
                        }],
                    },
                }],
            }],
        }
        result = WhatsAppService.parse_incoming_message(payload)
        self.assertIsNotNone(result)
        self.assertEqual(result["from_phone"], "+14155551234")
        self.assertEqual(result["text"], "What's my door code?")
        self.assertEqual(result["message_id"], "wamid.abc123")

    def test_returns_none_for_image(self):
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{"from": "14155551234", "type": "image"}],
                    },
                }],
            }],
        }
        result = WhatsAppService.parse_incoming_message(payload)
        self.assertIsNone(result)

    def test_returns_none_for_empty_payload(self):
        self.assertIsNone(WhatsAppService.parse_incoming_message({}))
        self.assertIsNone(WhatsAppService.parse_incoming_message({"entry": []}))

    def test_returns_none_for_status_update(self):
        payload = {
            "entry": [{
                "changes": [{
                    "value": {"statuses": [{"id": "wamid.xxx", "status": "delivered"}]},
                }],
            }],
        }
        result = WhatsAppService.parse_incoming_message(payload)
        self.assertIsNone(result)


@override_settings(WHATSAPP_VERIFY_TOKEN="my_token")
class TestVerifyWebhook(TestCase):
    def test_valid_verification(self):
        result = WhatsAppService.verify_webhook("subscribe", "my_token", "challenge_xyz")
        self.assertEqual(result, "challenge_xyz")

    def test_wrong_token(self):
        result = WhatsAppService.verify_webhook("subscribe", "wrong", "challenge_xyz")
        self.assertIsNone(result)

    def test_wrong_mode(self):
        result = WhatsAppService.verify_webhook("unsubscribe", "my_token", "challenge_xyz")
        self.assertIsNone(result)
