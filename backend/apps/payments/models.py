from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class PaymentRecord(TimeStampedModel):
    class PaymentType(models.TextChoices):
        CHARGE = "charge", "Charge"
        REFUND = "refund", "Refund"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"

    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.PROTECT,
        related_name="payment_records",
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    payment_intent_id = models.CharField(max_length=100, blank=True)
    charge_id = models.CharField(max_length=100, blank=True)
    refund_id = models.CharField(max_length=100, blank=True)
    failure_reason = models.TextField(blank=True)
    receipt_url = models.URLField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.payment_type} - {self.amount} {self.currency} ({self.status})"


class OwnerPayout(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payouts",
        limit_choices_to={"role": "owner"},
    )
    period_month = models.PositiveSmallIntegerField()
    period_year = models.PositiveSmallIntegerField()
    gross_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_rate_applied = models.DecimalField(max_digits=5, decimal_places=3)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    stripe_transfer_id = models.CharField(max_length=100, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("owner", "period_month", "period_year")]

    def __str__(self):
        return f"Payout {self.owner.email} - {self.period_month}/{self.period_year}"


class PayoutLineItem(TimeStampedModel):
    payout = models.ForeignKey(
        OwnerPayout,
        on_delete=models.CASCADE,
        related_name="line_items",
    )
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.PROTECT,
        related_name="payout_line_items",
    )
    reservation_total = models.DecimalField(max_digits=10, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    owner_amount = models.DecimalField(max_digits=10, decimal_places=2)
    guest_name = models.CharField(max_length=200)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    channel = models.CharField(max_length=20)

    class Meta:
        unique_together = [("payout", "reservation")]

    def __str__(self):
        return f"{self.guest_name} - {self.check_in_date} to {self.check_out_date}"
