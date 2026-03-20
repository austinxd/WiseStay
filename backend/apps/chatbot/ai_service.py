import json
import logging

from django.conf import settings
from django.db.models import F

from .context_builder import ContextBuilder
from .models import Conversation, Message
from .tools import CHATBOT_TOOLS, ToolExecutor

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 3
MAX_RESPONSE_TOKENS = 500


class AIConciergeService:
    """Orchestrates context -> GPT-4o -> tool execution -> response."""

    def __init__(self):
        from openai import OpenAI

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = getattr(settings, "OPENAI_MODEL", "gpt-4o")

    def process_message(self, conversation_id: int, user_message: str) -> str:
        conversation = Conversation.objects.select_related(
            "guest", "reservation",
        ).get(pk=conversation_id)

        guest_user_id = conversation.guest_id
        reservation_id = conversation.reservation_id

        # Save guest message
        Message.objects.create(
            conversation=conversation,
            sender_type="guest",
            content=user_message[:2000],
        )

        # Build context
        system_prompt = ContextBuilder.build_system_prompt(guest_user_id, reservation_id)
        history = ContextBuilder.get_conversation_history(conversation_id)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)

        tool_executor = ToolExecutor(guest_user_id, reservation_id)
        all_tool_calls = []

        try:
            response_text, tokens_prompt, tokens_completion = self._call_with_tools(
                messages, tool_executor, all_tool_calls,
            )
        except Exception as exc:
            logger.error(
                "AI service error for conversation %s: %s",
                conversation_id, exc, exc_info=True,
            )
            response_text = (
                "I'm having a little trouble right now. Please try again "
                "in a moment, or contact us at support@wisestay.com."
            )
            tokens_prompt = 0
            tokens_completion = 0

        # Save AI response
        Message.objects.create(
            conversation=conversation,
            sender_type="ai",
            content=response_text,
            ai_model=self.model,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tool_calls=all_tool_calls,
        )

        Conversation.objects.filter(pk=conversation_id).update(
            total_tokens_used=F("total_tokens_used") + tokens_prompt + tokens_completion,
        )

        return response_text

    def _call_with_tools(
        self,
        messages: list[dict],
        tool_executor: ToolExecutor,
        all_tool_calls: list,
    ) -> tuple[str, int, int]:
        """Returns (response_text, total_prompt_tokens, total_completion_tokens)."""
        total_prompt = 0
        total_completion = 0

        for iteration in range(MAX_TOOL_ITERATIONS):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=CHATBOT_TOOLS,
                tool_choice="auto",
                max_tokens=MAX_RESPONSE_TOKENS,
            )

            usage = response.usage
            if usage:
                total_prompt += usage.prompt_tokens
                total_completion += usage.completion_tokens

            choice = response.choices[0]
            message = choice.message

            if not message.tool_calls:
                return message.content or "", total_prompt, total_completion

            # Add assistant message with tool_calls
            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            for tc in message.tool_calls:
                func_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}

                result = tool_executor.execute(func_name, args)
                all_tool_calls.append({
                    "name": func_name,
                    "arguments": args,
                    "result": result[:500],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        # Max iterations — get final response without tools
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=MAX_RESPONSE_TOKENS,
        )
        if response.usage:
            total_prompt += response.usage.prompt_tokens
            total_completion += response.usage.completion_tokens

        return response.choices[0].message.content or "", total_prompt, total_completion
