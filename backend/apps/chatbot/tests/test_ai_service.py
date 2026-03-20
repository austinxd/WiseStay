from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.accounts.models import User
from apps.chatbot.ai_service import AIConciergeService, MAX_TOOL_ITERATIONS
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
        confirmation_code="WS-AI001",
        check_in_date=date.today() + timedelta(days=5),
        check_out_date=date.today() + timedelta(days=10),
        nights=5, guest_name="Test", nightly_rate=Decimal("200"),
        total_amount=Decimal("1000"),
    )
    conv = Conversation.objects.create(guest=guest, reservation=res, channel="web")
    return guest, conv


class TestAIConciergeService(TestCase):
    def setUp(self):
        self.guest, self.conv = _setup()

    @patch("apps.chatbot.ai_service.AIConciergeService.__init__", return_value=None)
    def test_process_message_direct_response(self, mock_init):
        """Test a simple response without tool calls."""
        service = AIConciergeService.__new__(AIConciergeService)
        service.model = "gpt-4o"

        # Mock the OpenAI client
        mock_client = MagicMock()
        service.client = mock_client

        # Simulate direct response (no tool calls)
        mock_message = MagicMock()
        mock_message.content = "Hello! Welcome to WiseStay."
        mock_message.tool_calls = None

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 20

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_client.chat.completions.create.return_value = mock_response

        result = service.process_message(self.conv.id, "Hi there!")

        self.assertEqual(result, "Hello! Welcome to WiseStay.")

        # Verify messages were saved
        guest_msgs = Message.objects.filter(conversation=self.conv, sender_type="guest")
        self.assertEqual(guest_msgs.count(), 1)
        self.assertEqual(guest_msgs.first().content, "Hi there!")

        ai_msgs = Message.objects.filter(conversation=self.conv, sender_type="ai")
        self.assertEqual(ai_msgs.count(), 1)
        self.assertEqual(ai_msgs.first().content, "Hello! Welcome to WiseStay.")
        self.assertEqual(ai_msgs.first().ai_model, "gpt-4o")

    @patch("apps.chatbot.ai_service.AIConciergeService.__init__", return_value=None)
    def test_process_message_with_tool_call(self, mock_init):
        """Test response with a tool call (get_loyalty_info)."""
        service = AIConciergeService.__new__(AIConciergeService)
        service.model = "gpt-4o"
        mock_client = MagicMock()
        service.client = mock_client

        # First call: GPT returns tool_call
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "get_loyalty_info"
        mock_tool_call.function.arguments = "{}"

        mock_msg1 = MagicMock()
        mock_msg1.content = ""
        mock_msg1.tool_calls = [mock_tool_call]

        mock_usage1 = MagicMock()
        mock_usage1.prompt_tokens = 150
        mock_usage1.completion_tokens = 30

        mock_resp1 = MagicMock()
        mock_resp1.choices = [MagicMock(message=mock_msg1)]
        mock_resp1.usage = mock_usage1

        # Second call: GPT returns text after receiving tool result
        mock_msg2 = MagicMock()
        mock_msg2.content = "You're a Bronze tier member with 0 points."
        mock_msg2.tool_calls = None

        mock_usage2 = MagicMock()
        mock_usage2.prompt_tokens = 200
        mock_usage2.completion_tokens = 25

        mock_resp2 = MagicMock()
        mock_resp2.choices = [MagicMock(message=mock_msg2)]
        mock_resp2.usage = mock_usage2

        mock_client.chat.completions.create.side_effect = [mock_resp1, mock_resp2]

        result = service.process_message(self.conv.id, "What's my loyalty status?")

        self.assertIn("Bronze", result)

        # Verify tool calls saved
        ai_msg = Message.objects.filter(conversation=self.conv, sender_type="ai").first()
        self.assertIsNotNone(ai_msg)
        self.assertTrue(len(ai_msg.tool_calls) > 0)
        self.assertEqual(ai_msg.tool_calls[0]["name"], "get_loyalty_info")

    @patch("apps.chatbot.ai_service.AIConciergeService.__init__", return_value=None)
    def test_handles_openai_error(self, mock_init):
        """Test graceful error handling when OpenAI fails."""
        service = AIConciergeService.__new__(AIConciergeService)
        service.model = "gpt-4o"
        mock_client = MagicMock()
        service.client = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API down")

        result = service.process_message(self.conv.id, "Hello")

        self.assertIn("trouble", result.lower())
        # AI message still saved
        ai_msg = Message.objects.filter(conversation=self.conv, sender_type="ai").first()
        self.assertIsNotNone(ai_msg)

    @patch("apps.chatbot.ai_service.AIConciergeService.__init__", return_value=None)
    def test_tool_loop_limited(self, mock_init):
        """Test that tool call loops are limited to MAX_TOOL_ITERATIONS."""
        service = AIConciergeService.__new__(AIConciergeService)
        service.model = "gpt-4o"
        mock_client = MagicMock()
        service.client = mock_client

        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_loop"
        mock_tool_call.function.name = "get_loyalty_info"
        mock_tool_call.function.arguments = "{}"

        mock_msg_with_tool = MagicMock()
        mock_msg_with_tool.content = ""
        mock_msg_with_tool.tool_calls = [mock_tool_call]

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 20

        mock_resp_tool = MagicMock()
        mock_resp_tool.choices = [MagicMock(message=mock_msg_with_tool)]
        mock_resp_tool.usage = mock_usage

        # Final response after loop exhaustion
        mock_msg_final = MagicMock()
        mock_msg_final.content = "Here is what I found."
        mock_msg_final.tool_calls = None

        mock_resp_final = MagicMock()
        mock_resp_final.choices = [MagicMock(message=mock_msg_final)]
        mock_resp_final.usage = mock_usage

        # Return tool calls for MAX_TOOL_ITERATIONS, then final
        side_effects = [mock_resp_tool] * MAX_TOOL_ITERATIONS + [mock_resp_final]
        mock_client.chat.completions.create.side_effect = side_effects

        result = service.process_message(self.conv.id, "Tell me everything")

        self.assertEqual(result, "Here is what I found.")
        # OpenAI called MAX_TOOL_ITERATIONS + 1 times
        self.assertEqual(
            mock_client.chat.completions.create.call_count,
            MAX_TOOL_ITERATIONS + 1,
        )
