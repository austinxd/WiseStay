from rest_framework import serializers

from .models import CalendarBlock, Property, PropertyAmenity, PropertyImage


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ["id", "url", "caption", "sort_order", "is_cover"]


class PropertyAmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyAmenity
        fields = ["id", "name", "category", "icon_name"]


class PropertyListSerializer(serializers.ModelSerializer):
    """Serializer for property list view (minimal data)."""

    images = PropertyImageSerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "slug",
            "name",
            "property_type",
            "city",
            "state",
            "country",
            "bedrooms",
            "bathrooms",
            "max_guests",
            "base_nightly_rate",
            "cleaning_fee",
            "guests_included",
            "extra_guest_fee",
            "currency",
            "images",
            "owner_name",
            "is_loyalty_eligible",
        ]


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Serializer for property detail view (full data)."""

    images = PropertyImageSerializer(many=True, read_only=True)
    amenities = PropertyAmenitySerializer(many=True, read_only=True)
    owner_name = serializers.CharField(source="owner.get_full_name", read_only=True)
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "slug",
            "name",
            "description",
            "property_type",
            "status",
            "address",
            "city",
            "state",
            "zip_code",
            "country",
            "latitude",
            "longitude",
            "bedrooms",
            "bathrooms",
            "max_guests",
            "beds",
            "base_nightly_rate",
            "cleaning_fee",
            "guests_included",
            "extra_guest_fee",
            "currency",
            "check_in_time",
            "check_out_time",
            "min_nights",
            "max_nights",
            "is_loyalty_eligible",
            "is_direct_booking_enabled",
            "meta_title",
            "meta_description",
            "images",
            "amenities",
            "owner_name",
            "owner_id",
            "created_at",
            "updated_at",
        ]


class CalendarBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarBlock
        fields = ["id", "start_date", "end_date", "block_type", "reason"]
