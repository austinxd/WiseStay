import logging

from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsOwner

from apps.domotics.models import NoiseAlert, SmartDevice
from apps.payments.models import OwnerPayout
from apps.properties.models import Property
from apps.reservations.models import Reservation

from .serializers import (
    OccupancyQuerySerializer,
    OwnerDeviceSerializer,
    OwnerNoiseAlertSerializer,
    OwnerPayoutDetailSerializer,
    OwnerPayoutListSerializer,
    OwnerProfileSerializer,
    OwnerPropertyDetailSerializer,
    OwnerPropertyListSerializer,
    OwnerReservationDetailSerializer,
    OwnerReservationListSerializer,
    PerformanceQuerySerializer,
    RevenueQuerySerializer,
)

logger = logging.getLogger(__name__)


class OwnerDashboardView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        from .services import OwnerDashboardService

        summary = OwnerDashboardService.get_dashboard_summary(request.user.id)
        return Response(summary)


class OwnerPropertiesListView(generics.ListAPIView):
    permission_classes = [IsOwner]
    serializer_class = OwnerPropertyListSerializer

    def get_queryset(self):
        return (
            Property.objects.filter(owner=self.request.user)
            .annotate(
                active_reservations_count=Count(
                    "reservations",
                    filter=Q(reservations__status__in=["confirmed", "checked_in"]),
                ),
                devices_count=Count("smart_devices"),
            )
            .prefetch_related("images")
            .order_by("name")
        )


class OwnerPropertyDetailView(generics.RetrieveAPIView):
    permission_classes = [IsOwner]
    serializer_class = OwnerPropertyDetailSerializer

    def get_queryset(self):
        return Property.objects.filter(
            owner=self.request.user,
        ).prefetch_related("images", "amenities")


class PropertyPerformanceView(APIView):
    permission_classes = [IsOwner]

    def get(self, request, pk):
        ser = PerformanceQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)

        from .services import OwnerDashboardService

        try:
            data = OwnerDashboardService.get_property_performance(
                pk, request.user.id, ser.validated_data.get("period", "ytd"),
            )
        except Property.DoesNotExist:
            return Response({"error": "Property not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(data)


class OwnerReservationsView(generics.ListAPIView):
    permission_classes = [IsOwner]
    serializer_class = OwnerReservationListSerializer

    def get_queryset(self):
        from .services import OwnerDashboardService

        return OwnerDashboardService.get_reservations_for_owner(
            owner_user_id=self.request.user.id,
            property_id=self.request.query_params.get("property_id"),
            status=self.request.query_params.get("status"),
            upcoming_only=self.request.query_params.get("upcoming") == "true",
        )


class OwnerReservationDetailView(generics.RetrieveAPIView):
    permission_classes = [IsOwner]
    serializer_class = OwnerReservationDetailSerializer

    def get_queryset(self):
        return Reservation.objects.filter(
            property__owner=self.request.user,
        ).select_related("property")


class RevenueReportView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        ser = RevenueQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)

        from .services import OwnerDashboardService

        data = OwnerDashboardService.get_revenue_report(
            request.user.id,
            ser.validated_data["year"],
            ser.validated_data.get("month"),
        )
        return Response(data)


class OccupancyCalendarView(APIView):
    permission_classes = [IsOwner]

    def get(self, request, pk):
        ser = OccupancyQuerySerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)

        from .services import OwnerDashboardService

        try:
            data = OwnerDashboardService.get_occupancy_calendar(
                pk, request.user.id,
                ser.validated_data["month"],
                ser.validated_data["year"],
            )
        except Property.DoesNotExist:
            return Response({"error": "Property not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(data)


class OwnerPayoutsView(generics.ListAPIView):
    permission_classes = [IsOwner]
    serializer_class = OwnerPayoutListSerializer

    def get_queryset(self):
        return OwnerPayout.objects.filter(
            owner=self.request.user,
        ).order_by("-period_year", "-period_month")


class OwnerPayoutDetailView(generics.RetrieveAPIView):
    permission_classes = [IsOwner]
    serializer_class = OwnerPayoutDetailSerializer

    def get_queryset(self):
        return OwnerPayout.objects.filter(
            owner=self.request.user,
        ).prefetch_related("line_items")


class OwnerDevicesView(APIView):
    permission_classes = [IsOwner]

    def get(self, request, pk):
        if not Property.objects.filter(pk=pk, owner=request.user).exists():
            return Response({"error": "Property not found"}, status=status.HTTP_404_NOT_FOUND)

        devices = SmartDevice.objects.filter(property_id=pk)
        return Response(OwnerDeviceSerializer(devices, many=True).data)


class OwnerNoiseAlertsView(generics.ListAPIView):
    permission_classes = [IsOwner]
    serializer_class = OwnerNoiseAlertSerializer

    def get_queryset(self):
        pk = self.kwargs["pk"]
        if not Property.objects.filter(pk=pk, owner=self.request.user).exists():
            return NoiseAlert.objects.none()
        return NoiseAlert.objects.filter(
            device__property_id=pk,
        ).order_by("-created_at")


class OwnerProfileView(APIView):
    permission_classes = [IsOwner]

    def get(self, request):
        profile = request.user.owner_profile
        data = {
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "company_name": profile.company_name,
            "commission_rate": profile.commission_rate,
            "stripe_connected": bool(profile.stripe_account_id),
            "is_payout_enabled": profile.is_payout_enabled,
            "payout_day": profile.payout_day,
        }
        return Response(data)

    def put(self, request):
        profile = request.user.owner_profile
        company = request.data.get("company_name")
        if company is not None:
            profile.company_name = company[:200]
            profile.save(update_fields=["company_name", "updated_at"])
        return self.get(request)
