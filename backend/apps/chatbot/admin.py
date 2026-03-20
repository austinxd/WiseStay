from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = (
        "sender_type",
        "content",
        "ai_model",
        "tokens_prompt",
        "tokens_completion",
        "tool_calls",
        "whatsapp_message_id",
        "created_at",
    )


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "guest",
        "reservation",
        "channel",
        "status",
        "total_tokens_used",
        "created_at",
    )
    list_filter = ("channel", "status")
    search_fields = ("guest__email",)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "sender_type",
        "content_preview",
        "ai_model",
        "created_at",
    )
    list_filter = ("sender_type", "ai_model")

    def content_preview(self, obj):
        return obj.content[:80]

    content_preview.short_description = "Content"
