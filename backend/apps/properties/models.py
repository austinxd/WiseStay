from datetime import time
from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Property(TimeStampedModel):
    class PropertyType(models.TextChoices):
        HOUSE = "house", "House"
        APARTMENT = "apartment", "Apartment"
        CONDO = "condo", "Condo"
        VILLA = "villa", "Villa"
        CABIN = "cabin", "Cabin"
        TOWNHOUSE = "townhouse", "Townhouse"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ONBOARDING = "onboarding", "Onboarding"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="properties",
        limit_choices_to={"role": "owner"},
    )
    hostaway_listing_id = models.CharField(
        max_length=50, unique=True, null=True, blank=True
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    property_type = models.CharField(
        max_length=20, choices=PropertyType.choices
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ONBOARDING
    )

    # Location
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=10)
    country = models.CharField(max_length=2, default="US")
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Capacity
    bedrooms = models.PositiveSmallIntegerField(default=1)
    bathrooms = models.DecimalField(
        max_digits=3, decimal_places=1, default=Decimal("1.0")
    )
    max_guests = models.PositiveSmallIntegerField(default=2)
    beds = models.PositiveSmallIntegerField(default=1)

    # Pricing
    base_nightly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    cleaning_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    currency = models.CharField(max_length=3, default="USD")

    # Policies
    check_in_time = models.TimeField(default=time(16, 0))
    check_out_time = models.TimeField(default=time(11, 0))
    min_nights = models.PositiveSmallIntegerField(default=1)
    max_nights = models.PositiveSmallIntegerField(default=365)

    # Features
    is_loyalty_eligible = models.BooleanField(default=True)
    is_direct_booking_enabled = models.BooleanField(default=True)

    # SEO
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    # Hostaway sync
    hostaway_last_synced_at = models.DateTimeField(null=True, blank=True)
    hostaway_raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "properties"
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["state", "city", "status"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.name


class PropertyImage(TimeStampedModel):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="images"
    )
    url = models.URLField(max_length=500)
    caption = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    hostaway_image_id = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.property.name} - Image {self.sort_order}"


class PropertyAmenity(TimeStampedModel):
    class Category(models.TextChoices):
        ESSENTIALS = "essentials", "Essentials"
        KITCHEN = "kitchen", "Kitchen"
        OUTDOOR = "outdoor", "Outdoor"
        ENTERTAINMENT = "entertainment", "Entertainment"
        SAFETY = "safety", "Safety"
        ACCESSIBILITY = "accessibility", "Accessibility"
        PARKING = "parking", "Parking"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="amenities"
    )
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=Category.choices)
    icon_name = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural = "property amenities"
        unique_together = [("property", "name")]

    def __str__(self):
        return f"{self.property.name} - {self.name}"


class CalendarBlock(TimeStampedModel):
    class BlockType(models.TextChoices):
        OWNER_BLOCK = "owner_block", "Owner Block"
        MAINTENANCE = "maintenance", "Maintenance"
        HOSTAWAY_SYNC = "hostaway_sync", "Hostaway Sync"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="calendar_blocks"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    block_type = models.CharField(max_length=20, choices=BlockType.choices)
    reason = models.CharField(max_length=200, blank=True)
    hostaway_calendar_id = models.CharField(max_length=50, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["property", "start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.property.name}: {self.start_date} to {self.end_date}"
