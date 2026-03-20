import random
import string
from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import TimeStampedModel


class User(AbstractUser):
    class Role(models.TextChoices):
        GUEST = "guest", "Guest"
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.GUEST,
    )
    phone = models.CharField(max_length=20, blank=True)
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    avatar_url = models.URLField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return self.email


class GuestProfile(TimeStampedModel):
    class LoyaltyTier(models.TextChoices):
        BRONZE = "bronze", "Bronze"
        SILVER = "silver", "Silver"
        GOLD = "gold", "Gold"
        PLATINUM = "platinum", "Platinum"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="guest_profile",
    )
    loyalty_tier = models.CharField(
        max_length=10,
        choices=LoyaltyTier.choices,
        default=LoyaltyTier.BRONZE,
    )
    points_balance = models.PositiveIntegerField(default=0)
    direct_bookings_count = models.PositiveIntegerField(default=0)
    successful_referrals_count = models.PositiveIntegerField(default=0)
    preferences = models.JSONField(default=dict, blank=True)
    referral_code = models.CharField(
        max_length=10,
        unique=True,
        editable=False,
    )
    hostaway_guest_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
    )

    def __str__(self):
        return f"{self.user.email} - {self.loyalty_tier}"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self._generate_referral_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_referral_code():
        chars = string.ascii_uppercase + string.digits
        while True:
            code = "WS-" + "".join(random.choices(chars, k=4))
            if not GuestProfile.objects.filter(referral_code=code).exists():
                return code


class OwnerProfile(TimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="owner_profile",
    )
    company_name = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(max_length=20, blank=True)
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=3,
        default=Decimal("0.200"),
    )
    stripe_account_id = models.CharField(max_length=50, blank=True)
    payout_day = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
    )
    is_payout_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.company_name or 'Individual'}"
