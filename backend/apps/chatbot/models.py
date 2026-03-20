from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Conversation(TimeStampedModel):
    CHANNEL_CHOICES = [
        ("web", "Web"),
        ("app", "App"),
        ("whatsapp", "WhatsApp"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("escalated", "Escalated"),
        ("resolved", "Resolved"),
        ("archived", "Archived"),
    ]

    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        limit_choices_to={"role": "guest"},
    )
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    channel = models.CharField(
        max_length=20, choices=CHANNEL_CHOICES, default="web"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active"
    )
    whatsapp_thread_id = models.CharField(max_length=100, blank=True)
    total_tokens_used = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Conversation"
        verbose_name_plural = "Conversations"

    def __str__(self):
        return f"Conversation {self.id} - {self.guest.email} ({self.status})"


class Message(TimeStampedModel):
    SENDER_TYPE_CHOICES = [
        ("guest", "Guest"),
        ("ai", "AI"),
        ("system", "System"),
        ("human", "Human"),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPE_CHOICES)
    content = models.TextField()
    ai_model = models.CharField(max_length=50, blank=True)
    tokens_prompt = models.PositiveIntegerField(default=0)
    tokens_completion = models.PositiveIntegerField(default=0)
    tool_calls = models.JSONField(default=list, blank=True)
    whatsapp_message_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"{self.sender_type}: {self.content[:50]}"
