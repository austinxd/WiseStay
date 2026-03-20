from django.db import models

from common.models import TimeStampedModel


class HostawayCredential(TimeStampedModel):
    client_id = models.CharField(max_length=100)
    client_secret = models.TextField(help_text="Encrypted via common.utils.encryption")
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    webhook_secret = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Hostaway Credential"
        verbose_name_plural = "Hostaway Credentials"

    def __str__(self):
        return f"Hostaway Credential ({self.client_id})"


class SyncLog(TimeStampedModel):
    SYNC_TYPE_CHOICES = [
        ("listings", "Listings"),
        ("calendar", "Calendar"),
        ("reservations", "Reservations"),
        ("messages", "Messages"),
    ]

    STATUS_CHOICES = [
        ("started", "Started"),
        ("success", "Success"),
        ("partial", "Partial"),
        ("failed", "Failed"),
    ]

    sync_type = models.CharField(max_length=20, choices=SYNC_TYPE_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="started"
    )
    items_processed = models.PositiveIntegerField(default=0)
    items_created = models.PositiveIntegerField(default=0)
    items_updated = models.PositiveIntegerField(default=0)
    items_failed = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)
    triggered_by = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g. 'celery', 'webhook', 'manual'",
    )

    class Meta:
        verbose_name = "Sync Log"
        verbose_name_plural = "Sync Logs"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Sync {self.sync_type} - {self.status} ({self.started_at})"
