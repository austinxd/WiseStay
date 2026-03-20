import logging

from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsGuest

from .models import Conversation, Message
from .serializers import (
    ConversationDetailSerializer,
    ConversationListSerializer,
    MessageSerializer,
    SendMessageSerializer,
    StartConversationSerializer,
)

logger = logging.getLogger(__name__)


class StartConversationView(APIView):
    permission_classes = [IsGuest]

    def post(self, request):
        serializer = StartConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reservation_id = serializer.validated_data.get("reservation_id")
        channel = serializer.validated_data.get("channel", "web")

        # Return existing active conversation if one exists
        existing = Conversation.objects.filter(
            guest=request.user,
            status="active",
            channel=channel,
        )
        if reservation_id:
            existing = existing.filter(reservation_id=reservation_id)

        conv = existing.first()
        if conv:
            return Response({
                "conversation_id": conv.id,
                "status": conv.status,
                "is_new": False,
            })

        conv = Conversation.objects.create(
            guest=request.user,
            reservation_id=reservation_id,
            channel=channel,
            status="active",
        )

        return Response({
            "conversation_id": conv.id,
            "status": "active",
            "is_new": True,
        }, status=status.HTTP_201_CREATED)


class ConversationListView(generics.ListAPIView):
    permission_classes = [IsGuest]
    serializer_class = ConversationListSerializer

    def get_queryset(self):
        return Conversation.objects.filter(
            guest=self.request.user,
        ).prefetch_related("messages").order_by("-created_at")


class ConversationDetailView(generics.RetrieveAPIView):
    permission_classes = [IsGuest]
    serializer_class = ConversationDetailSerializer

    def get_queryset(self):
        return Conversation.objects.filter(
            guest=self.request.user,
        ).prefetch_related("messages")


class SendMessageView(APIView):
    """REST fallback for clients that don't use WebSocket."""

    permission_classes = [IsGuest]

    def post(self, request, conversation_id):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            conv = Conversation.objects.get(
                pk=conversation_id, guest=request.user,
            )
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        from .ai_service import AIConciergeService

        try:
            service = AIConciergeService()
            response_text = service.process_message(
                conv.id, serializer.validated_data["content"],
            )
        except Exception as exc:
            logger.error("SendMessage error: %s", exc, exc_info=True)
            return Response(
                {"error": "Failed to process message"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        ai_msg = conv.messages.filter(sender_type="ai").order_by("-created_at").first()

        return Response({
            "message_id": ai_msg.id if ai_msg else None,
            "content": response_text,
            "sender_type": "ai",
        })


class MessageHistoryView(generics.ListAPIView):
    permission_classes = [IsGuest]
    serializer_class = MessageSerializer

    def get_queryset(self):
        return Message.objects.filter(
            conversation_id=self.kwargs["conversation_id"],
            conversation__guest=self.request.user,
        ).order_by("created_at")


class WhatsAppWebhookView(APIView):
    """Receives WhatsApp Business API webhooks."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        """Webhook verification from Meta."""
        from .whatsapp_service import WhatsAppService

        mode = request.query_params.get("hub.mode", "")
        token = request.query_params.get("hub.verify_token", "")
        challenge = request.query_params.get("hub.challenge", "")

        result = WhatsAppService.verify_webhook(mode, token, challenge)
        if result is not None:
            return HttpResponse(result, content_type="text/plain")
        return Response({"error": "Verification failed"}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        """Incoming WhatsApp messages."""
        from apps.accounts.models import User

        from .whatsapp_service import WhatsAppService

        parsed = WhatsAppService.parse_incoming_message(request.data)
        if not parsed:
            return Response({"status": "ignored"})

        from_phone = parsed["from_phone"]
        text = parsed["text"]

        if not text:
            return Response({"status": "ignored"})

        # Find guest by phone
        try:
            user = User.objects.get(phone=from_phone, role="guest", is_active=True)
        except User.DoesNotExist:
            logger.info("WhatsApp from unregistered number: %s", from_phone)
            return Response({"status": "ok"})

        # Find or create conversation
        conv, _ = Conversation.objects.get_or_create(
            guest=user,
            channel="whatsapp",
            status="active",
            defaults={"whatsapp_thread_id": from_phone},
        )

        # Process message
        try:
            from .ai_service import AIConciergeService

            service = AIConciergeService()
            response_text = service.process_message(conv.id, text)

            WhatsAppService.send_message(from_phone, response_text)
        except Exception as exc:
            logger.error("WhatsApp processing error: %s", exc, exc_info=True)

        return Response({"status": "ok"})
