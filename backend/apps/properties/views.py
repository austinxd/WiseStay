from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CalendarBlock, Property
from .serializers import (
    CalendarBlockSerializer,
    PropertyDetailSerializer,
    PropertyListSerializer,
)


class PropertyFilter(filters.FilterSet):
    """Filter for properties."""

    city = filters.CharFilter(lookup_expr="icontains")
    state = filters.CharFilter(lookup_expr="iexact")
    property_type = filters.CharFilter(lookup_expr="iexact")
    min_price = filters.NumberFilter(field_name="base_nightly_rate", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="base_nightly_rate", lookup_expr="lte")
    bedrooms = filters.NumberFilter(lookup_expr="gte")
    max_guests = filters.NumberFilter(lookup_expr="gte")
    is_loyalty_eligible = filters.BooleanFilter()

    class Meta:
        model = Property
        fields = [
            "city",
            "state",
            "property_type",
            "bedrooms",
            "max_guests",
            "is_loyalty_eligible",
        ]


class PropertyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing and retrieving properties.

    list: GET /api/v1/properties/
    retrieve: GET /api/v1/properties/{slug}/
    """

    permission_classes = [AllowAny]
    filterset_class = PropertyFilter
    search_fields = ["name", "city", "state", "description"]
    ordering_fields = ["base_nightly_rate", "bedrooms", "max_guests", "created_at"]
    ordering = ["-created_at"]
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Property.objects.filter(status=Property.Status.ACTIVE)
            .select_related("owner")
            .prefetch_related("images", "amenities")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PropertyDetailSerializer
        return PropertyListSerializer

    @action(detail=True, methods=["get"])
    def calendar(self, request, slug=None):
        """Get calendar blocks for a property."""
        property_obj = self.get_object()
        blocks = CalendarBlock.objects.filter(property=property_obj)
        serializer = CalendarBlockSerializer(blocks, many=True)
        return Response(serializer.data)
