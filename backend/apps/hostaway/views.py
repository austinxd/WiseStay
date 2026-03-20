import base64
import logging

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.throttles import WebhookRateThrottle

from .models import HostawayCredential, SyncLog
from .serializers import ManualSyncSerializer, SyncLogSerializer
from .tasks import (
    process_webhook_event,
    sync_calendar_task,
    sync_listings_task,
    sync_reservations_task,
)

logger = logging.getLogger(__name__)

# Mapping of Hostaway webhook event types to our processor names
EVENT_TYPE_MAP = {
    "reservationCreated": "reservation_created",
    "reservationUpdated": "reservation_updated",
    "reservation_created": "reservation_created",
    "reservation_updated": "reservation_updated",
    "conversationMessageCreated": "message_received",
    "conversation_message_created": "message_received",
}


class HostawayWebhookView(APIView):
    """
    Unified webhook endpoint for all Hostaway events.

    - Validates optional Basic Auth against HostawayCredential.webhook_secret
    - Dispatches processing to Celery for async execution
    - Always returns 200 for valid payloads (Hostaway retries on non-200)
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [WebhookRateThrottle]

    def post(self, request):
        # Optional Basic Auth validation
        if not self._validate_auth(request):
            return Response(
                {"error": "Invalid webhook authentication"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        payload = request.data
        if not isinstance(payload, dict):
            logger.warning("Webhook: received non-dict payload: %s", type(payload))
            return Response(
                {"error": "Invalid payload format"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Detect event type — Hostaway uses different field names
        event_type = (
            payload.get("event")
            or payload.get("eventType")
            or payload.get("event_type")
            or ""
        )

        mapped_event = EVENT_TYPE_MAP.get(event_type)
        if not mapped_event:
            logger.warning("Webhook: unknown event type '%s'", event_type)
            # Still return 200 to prevent Hostaway from retrying
            return Response({"status": "ignored", "event": event_type})

        # Dispatch to Celery for async processing
        process_webhook_event.delay(mapped_event, payload)

        logger.info("Webhook: dispatched event '%s' to Celery", event_type)
        return Response({"status": "accepted", "event": event_type})

    def _validate_auth(self, request) -> bool:
        """Validate Basic Auth if webhook_secret is configured."""
        cred = HostawayCredential.objects.filter(is_active=True).first()
        if not cred or not cred.webhook_secret:
            # No secret configured — accept but log warning
            if cred and not cred.webhook_secret:
                logger.warning("Webhook: no webhook_secret configured — accepting without auth")
            return True

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Basic "):
            return False

        try:
            decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
            # The webhook_secret stores "username:password"
            return decoded == cred.webhook_secret
        except Exception:
            return False


class ManualSyncListingsView(APIView):
    """Manually trigger a listings sync. Admin only."""

    permission_classes = [IsAdminUser]

    def post(self, request):
        sync_listings_task.delay()
        return Response(
            {"status": "started", "message": "Listings sync dispatched"},
            status=status.HTTP_202_ACCEPTED,
        )


class ManualSyncReservationsView(APIView):
    """Manually trigger a reservations sync. Admin only."""

    permission_classes = [IsAdminUser]

    def post(self, request):
        sync_reservations_task.delay()
        return Response(
            {"status": "started", "message": "Reservations sync dispatched"},
            status=status.HTTP_202_ACCEPTED,
        )


class ManualSyncCalendarView(APIView):
    """Manually trigger a calendar sync. Admin only."""

    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = ManualSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        property_id = serializer.validated_data.get("property_id")
        sync_calendar_task.delay(property_id=property_id)
        return Response(
            {"status": "started", "message": "Calendar sync dispatched"},
            status=status.HTTP_202_ACCEPTED,
        )


class SyncLogListView(generics.ListAPIView):
    """List sync logs. Admin only."""

    permission_classes = [IsAdminUser]
    serializer_class = SyncLogSerializer
    queryset = SyncLog.objects.all()
    filterset_fields = ["sync_type", "status", "triggered_by"]
    ordering_fields = ["started_at", "completed_at"]
    ordering = ["-started_at"]
