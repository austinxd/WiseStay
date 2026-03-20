import logging

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsOwner
from common.throttles import WebhookRateThrottle

from .models import OwnerPayout
from .serializers import (
    OwnerPayoutDetailSerializer,
    OwnerPayoutListSerializer,
    StripeConnectOnboardSerializer,
)

logger = logging.getLogger(__name__)


class StripeWebhookView(APIView):
    """Receives and processes Stripe webhook events."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [WebhookRateThrottle]

    def post(self, request):
        from .stripe_service import StripeService

        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            event = StripeService.verify_webhook_signature(payload, sig_header)
        except Exception as e:
            logger.warning("Stripe webhook signature verification failed: %s", e)
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event.get("type", "")
        data = event.get("data", {}).get("object", {})

        try:
            if event_type == "payment_intent.succeeded":
                self._handle_payment_succeeded(data)
            elif event_type == "payment_intent.payment_failed":
                self._handle_payment_failed(data)
            elif event_type == "charge.refunded":
                self._handle_charge_refunded(data)
        except Exception:
            logger.exception("Error processing Stripe webhook event %s", event_type)

        return Response({"status": "ok"})

    def _handle_payment_succeeded(self, data):
        pi_id = data.get("id", "")
        metadata = data.get("metadata", {})
        reservation_id = metadata.get("reservation_id")

        if not reservation_id:
            logger.warning("payment_intent.succeeded without reservation_id: %s", pi_id)
            return

        from apps.reservations.services import ReservationService

        try:
            ReservationService.confirm_booking(int(reservation_id), pi_id)
            logger.info("Booking confirmed via webhook: reservation %s", reservation_id)
        except Exception:
            logger.exception("Failed to confirm booking %s", reservation_id)

    def _handle_payment_failed(self, data):
        from .models import PaymentRecord

        pi_id = data.get("id", "")
        failure = data.get("last_payment_error", {})
        message = failure.get("message", "Payment failed")

        updated = PaymentRecord.objects.filter(
            payment_intent_id=pi_id, status="pending",
        ).update(status="failed", failure_reason=message)

        if updated:
            logger.info("Payment failed for PI %s: %s", pi_id, message)

    def _handle_charge_refunded(self, data):
        from .models import PaymentRecord

        pi_id = data.get("payment_intent", "")
        PaymentRecord.objects.filter(
            payment_intent_id=pi_id, payment_type="charge", status="succeeded",
        ).update(status="refunded")


class OwnerPayoutsView(generics.ListAPIView):
    permission_classes = [IsOwner]
    serializer_class = OwnerPayoutListSerializer

    def get_queryset(self):
        return OwnerPayout.objects.filter(
            owner=self.request.user,
        ).order_by("-period_year", "-period_month")


class PayoutDetailView(generics.RetrieveAPIView):
    serializer_class = OwnerPayoutDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return OwnerPayout.objects.prefetch_related("line_items").all()
        return OwnerPayout.objects.prefetch_related("line_items").filter(owner=user)


class AdminPayoutApproveView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        from .payout_service import PayoutService

        try:
            payout = PayoutService.approve_payout(pk, request.user.id)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OwnerPayoutDetailSerializer(payout).data)


class StripeConnectOnboardView(APIView):
    permission_classes = [IsOwner]

    def post(self, request):
        serializer = StripeConnectOnboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .stripe_service import StripeService

        try:
            url = StripeService.create_connect_account_link(
                owner_user_id=request.user.id,
                return_url=serializer.validated_data["return_url"],
                refresh_url=serializer.validated_data["refresh_url"],
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"onboarding_url": url})
