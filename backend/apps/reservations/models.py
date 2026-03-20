from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Reservation(TimeStampedModel):
    class Channel(models.TextChoices):
        DIRECT = "direct", "Direct"
        AIRBNB = "airbnb", "Airbnb"
        BOOKING = "booking", "Booking"
        VRBO = "vrbo", "VRBO"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked In"
        CHECKED_OUT = "checked_out", "Checked Out"
        CANCELLED = "cancelled", "Cancelled"
        DECLINED = "declined", "Declined"

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    guest_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
        limit_choices_to={"role": "guest"},
    )

    # External IDs
    hostaway_reservation_id = models.CharField(
        max_length=50, unique=True, null=True, blank=True
    )

    # Booking details
    channel = models.CharField(
        max_length=20, choices=Channel.choices, default=Channel.DIRECT
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    confirmation_code = models.CharField(max_length=50, unique=True)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    nights = models.PositiveSmallIntegerField()
    guests_count = models.PositiveSmallIntegerField(default=1)

    # Guest info
    guest_name = models.CharField(max_length=200)
    guest_email = models.EmailField(blank=True)
    guest_phone = models.CharField(max_length=20, blank=True)

    # Financials
    nightly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    cleaning_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    service_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    taxes = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    discount_amount = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )

    # Loyalty
    points_earned = models.PositiveIntegerField(default=0)
    points_redeemed = models.PositiveIntegerField(default=0)

    # Payment
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)

    # Timestamps
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)

    # Notes
    internal_notes = models.TextField(blank=True)
    guest_notes = models.TextField(blank=True)

    # Raw data
    hostaway_raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-check_in_date"]
        indexes = [
            models.Index(
                fields=["property", "check_in_date", "check_out_date"]
            ),
            models.Index(fields=["guest_user", "status"]),
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["check_in_date"]),
        ]

    def __str__(self):
        return f"{self.confirmation_code} - {self.property.name}"
