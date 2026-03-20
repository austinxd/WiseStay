import logging

from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsGuest

from .models import PointTransaction, TierConfig
from .referral_service import ReferralService
from .serializers import (
    ApplyReferralSerializer,
    CalculateDiscountSerializer,
    PointTransactionSerializer,
    RedeemPointsSerializer,
    TierConfigPublicSerializer,
)
from .services import LoyaltyService

logger = logging.getLogger(__name__)


class LoyaltyDashboardView(APIView):
    permission_classes = [IsGuest]

    def get(self, request):
        summary = LoyaltyService.get_guest_loyalty_summary(request.user.id)
        return Response(summary)


class PointsHistoryView(generics.ListAPIView):
    permission_classes = [IsGuest]
    serializer_class = PointTransactionSerializer

    def get_queryset(self):
        qs = PointTransaction.objects.filter(guest=self.request.user)
        tx_type = self.request.query_params.get("type")
        if tx_type:
            qs = qs.filter(transaction_type=tx_type)
        return qs


class RedeemPointsView(APIView):
    permission_classes = [IsGuest]

    def post(self, request):
        serializer = RedeemPointsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pt, discount = LoyaltyService.redeem_points(
                guest_user_id=request.user.id,
                points_to_redeem=serializer.validated_data["points"],
                reservation_id=serializer.validated_data.get("reservation_id"),
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        from apps.accounts.models import GuestProfile
        profile = GuestProfile.objects.get(user=request.user)

        return Response({
            "discount_amount": float(discount),
            "new_balance": profile.points_balance,
            "transaction_id": pt.id,
        })


class CalculateDiscountView(APIView):
    permission_classes = [IsGuest]

    def post(self, request):
        serializer = CalculateDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = LoyaltyService.calculate_booking_discount(
            guest_user_id=request.user.id,
            base_amount=serializer.validated_data["base_amount"],
        )
        return Response(result)


class ReferralInfoView(APIView):
    permission_classes = [IsGuest]

    def get(self, request):
        stats = ReferralService.get_referral_stats(request.user.id)
        return Response(stats)


class ApplyReferralCodeView(APIView):
    permission_classes = [IsGuest]

    def post(self, request):
        serializer = ApplyReferralSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            referral = ReferralService.create_referral(
                referrer_code=serializer.validated_data["referral_code"],
                referred_user_id=request.user.id,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        referrer_name = referral.referrer.get_full_name() or referral.referrer.email
        return Response({
            "status": "pending",
            "referrer_name": referrer_name,
        }, status=status.HTTP_201_CREATED)


class TierInfoView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = TierConfigPublicSerializer
    queryset = TierConfig.objects.filter(is_active=True).order_by("sort_order")
    pagination_class = None
