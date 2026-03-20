from rest_framework import serializers

from .models import Conversation, Message


class StartConversationSerializer(serializers.Serializer):
    reservation_id = serializers.IntegerField(required=False)
    channel = serializers.ChoiceField(
        choices=["web", "app", "whatsapp"], default="web",
    )


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(min_length=1, max_length=2000)


class MessageSerializer(serializers.ModelSerializer):
    tool_calls_summary = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id", "sender_type", "content", "created_at",
            "tool_calls_summary",
        ]

    def get_tool_calls_summary(self, obj):
        if not obj.tool_calls:
            return []
        return [
            {"name": tc.get("name"), "result": tc.get("result", "")[:200]}
            for tc in obj.tool_calls
        ]


class ConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id", "channel", "status", "created_at", "last_message",
        ]

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        if msg:
            return msg.content[:100]
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id", "channel", "status", "total_tokens_used",
            "created_at", "messages",
        ]

    def get_messages(self, obj):
        msgs = obj.messages.order_by("-created_at")[:50]
        return MessageSerializer(reversed(list(msgs)), many=True).data
