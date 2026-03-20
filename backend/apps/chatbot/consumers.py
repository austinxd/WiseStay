import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat with AI concierge."""

    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.guest_user = None

        # Authenticate via JWT token in query string
        user = await self._authenticate()
        if user is None:
            await self.close(code=4001)
            return

        # Verify ownership
        owns = await self._verify_ownership(user.id)
        if not owns:
            await self.close(code=4003)
            return

        self.guest_user = user
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                "type": "error", "content": "Invalid JSON",
            }))
            return

        content = data.get("content", "").strip()
        if not content:
            return

        if len(content) > 2000:
            content = content[:2000]

        try:
            # Process and stream response
            full_response = ""
            chunks = await database_sync_to_async(self._process_message)(content)
            full_response = chunks

            await self.send(text_data=json.dumps({
                "type": "message_complete",
                "content": full_response,
            }))
        except Exception as exc:
            logger.error("Chat consumer error: %s", exc, exc_info=True)
            await self.send(text_data=json.dumps({
                "type": "error",
                "content": "Something went wrong. Please try again.",
            }))

    def _process_message(self, content: str) -> str:
        from .ai_service import AIConciergeService

        service = AIConciergeService()
        return service.process_message(self.conversation_id, content)

    @database_sync_to_async
    def _authenticate(self):
        """Authenticate user from JWT token in query string."""
        from urllib.parse import parse_qs

        query_string = self.scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        if not token:
            return None

        try:
            from rest_framework_simplejwt.tokens import AccessToken

            access = AccessToken(token)
            from apps.accounts.models import User

            return User.objects.get(pk=access["user_id"], role="guest", is_active=True)
        except Exception:
            return None

    @database_sync_to_async
    def _verify_ownership(self, user_id: int) -> bool:
        from .models import Conversation

        return Conversation.objects.filter(
            pk=self.conversation_id, guest_id=user_id,
        ).exists()
