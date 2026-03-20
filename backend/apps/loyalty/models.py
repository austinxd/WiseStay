from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class PointTransaction(TimeStampedModel):
    class TransactionType(models.TextChoices):
        EARN = "earn", "Earn"
        REDEEM = "redeem", "Redeem"
        EXPIRE = "expire", "Expire"
        ADJUST = "adjust", "Adjust"
        BONUS = "bonus", "Bonus"
        REFERRAL_BONUS = "referral_bonus", "Referral Bonus"

    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="point_transactions",
        limit_choices_to={"role": "guest"},
    )
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="point_transactions",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
    )
    points = models.IntegerField(
        help_text="Positive for earn/bonus, negative for redeem/expire.",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Only for earn transactions; 12 months after creation.",
    )
    points_remaining = models.IntegerField(
        default=0,
        help_text="Only for earn type; starts equal to points, decreases with FIFO redemption.",
    )
    balance_after = models.IntegerField(
        help_text="Guest's point balance after this transaction.",
    )
    description = models.CharField(max_length=200)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["guest", "transaction_type"]),
            models.Index(
                fields=["expires_at"],
                condition=models.Q(expires_at__isnull=False),
                name="idx_pt_expires_at_not_null",
            ),
        ]

    def __str__(self):
        return f"{self.transaction_type}: {self.points} pts ({self.guest.email})"


class TierConfig(TimeStampedModel):
    class TierName(models.TextChoices):
        BRONZE = "bronze", "Bronze"
        SILVER = "silver", "Silver"
        GOLD = "gold", "Gold"
        PLATINUM = "platinum", "Platinum"

    tier_name = models.CharField(
        max_length=10,
        unique=True,
        choices=TierName.choices,
    )
    min_reservations = models.PositiveIntegerField(default=0)
    min_referrals = models.PositiveIntegerField(default=0)
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    early_checkin = models.BooleanField(default=False)
    late_checkout = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    bonus_points_on_upgrade = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.tier_name.title()} Tier"


class Referral(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referrals_made",
        limit_choices_to={"role": "guest"},
    )
    referred_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_received",
        limit_choices_to={"role": "guest"},
    )
    referral_code_used = models.CharField(max_length=10)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default="pending",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    reward_points_granted = models.PositiveIntegerField(default=0)
    referred_reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referral",
    )

    def __str__(self):
        return f"{self.referrer.email} -> {self.referred_user.email} ({self.status})"


class TierHistory(TimeStampedModel):
    class TriggeredBy(models.TextChoices):
        RESERVATION_COMPLETED = "reservation_completed", "Reservation Completed"
        REFERRAL_COMPLETED = "referral_completed", "Referral Completed"
        ADMIN_ADJUSTMENT = "admin_adjustment", "Admin Adjustment"

    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tier_history",
        limit_choices_to={"role": "guest"},
    )
    previous_tier = models.CharField(max_length=10)
    new_tier = models.CharField(max_length=10)
    reason = models.CharField(max_length=200)
    triggered_by = models.CharField(
        max_length=30,
        choices=TriggeredBy.choices,
    )

    def __str__(self):
        return f"{self.guest.email}: {self.previous_tier} -> {self.new_tier}"
