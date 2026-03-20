import logging

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsGuest, IsOwner

from .models import Reservation
from .serializers import (
    CalendarQuerySerializer,
    CancelBookingSerializer,
    CheckAvailabilitySerializer,
    CreateBookingSerializer,
    PriceCalculationSerializer,
    ReservationDetailSerializer,
    ReservationListSerializer,
)

logger = logging.getLogger(__name__)


class CheckAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        serializer = CheckAvailabilitySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        from .availability import AvailabilityService

        result = AvailabilityService.check_availability(
            property_id=serializer.validated_data["property_id"],
            check_in=serializer.validated_data["check_in"],
            check_out=serializer.validated_data["check_out"],
        )
        return Response(result)


class CalendarAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, property_id):
        serializer = CalendarQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        from .availability import AvailabilityService

        result = AvailabilityService.get_available_dates(
            property_id=property_id,
            month=serializer.validated_data["month"],
            year=serializer.validated_data["year"],
        )
        return Response(result)


class PriceCalculationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PriceCalculationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .pricing import PricingService

        guest_id = request.user.id if request.user.is_authenticated else None
        points = serializer.validated_data.get("points_to_redeem", 0)

        if points > 0 and guest_id:
            result = PricingService.calculate_final_amount(
                property_id=serializer.validated_data["property_id"],
                check_in=serializer.validated_data["check_in"],
                check_out=serializer.validated_data["check_out"],
                guest_user_id=guest_id,
                points_to_redeem=points,
            )
        else:
            result = PricingService.calculate_price(
                property_id=serializer.validated_data["property_id"],
                check_in=serializer.validated_data["check_in"],
                check_out=serializer.validated_data["check_out"],
                guest_user_id=guest_id,
            )
        return Response(result)


class CreateBookingView(APIView):
    permission_classes = [IsGuest]

    def post(self, request):
        serializer = CreateBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .services import ReservationService

        try:
            result = ReservationService.initiate_direct_booking(
                guest_user_id=request.user.id,
                property_id=serializer.validated_data["property_id"],
                check_in=serializer.validated_data["check_in"],
                check_out=serializer.validated_data["check_out"],
                guests_count=serializer.validated_data["guests_count"],
                points_to_redeem=serializer.validated_data.get("points_to_redeem", 0),
                guest_notes=serializer.validated_data.get("guest_notes", ""),
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_201_CREATED)


class GuestReservationsView(generics.ListAPIView):
    permission_classes = [IsGuest]
    serializer_class = ReservationListSerializer

    def get_queryset(self):
        qs = Reservation.objects.filter(
            guest_user=self.request.user
        ).select_related("property").order_by("-check_in_date")

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        from datetime import date

        if self.request.query_params.get("upcoming") == "true":
            qs = qs.filter(check_in_date__gte=date.today())
        elif self.request.query_params.get("past") == "true":
            qs = qs.filter(check_out_date__lt=date.today())

        return qs


class ReservationDetailView(generics.RetrieveAPIView):
    serializer_class = ReservationDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "admin":
            return Reservation.objects.select_related("property").all()
        elif user.role == "owner":
            return Reservation.objects.select_related("property").filter(
                property__owner=user,
            )
        else:
            return Reservation.objects.select_related("property").filter(
                guest_user=user,
            )


class CancelBookingView(APIView):
    permission_classes = [IsGuest | IsAdminUser]

    def post(self, request, pk):
        serializer = CancelBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Verify the guest owns this reservation
        try:
            reservation = Reservation.objects.get(pk=pk)
            if request.user.role == "guest" and reservation.guest_user_id != request.user.id:
                return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        except Reservation.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        from .services import ReservationService

        try:
            result = ReservationService.cancel_booking(
                reservation_id=pk,
                cancelled_by=request.user.role,
                reason=serializer.validated_data.get("reason", ""),
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ReservationDetailSerializer(result).data)
