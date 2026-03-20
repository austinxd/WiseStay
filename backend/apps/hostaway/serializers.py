from rest_framework import serializers

from .models import SyncLog


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncLog
        fields = [
            "id",
            "sync_type",
            "status",
            "items_processed",
            "items_created",
            "items_updated",
            "items_failed",
            "started_at",
            "completed_at",
            "error_message",
            "error_details",
            "triggered_by",
            "created_at",
        ]
        read_only_fields = fields


class ManualSyncSerializer(serializers.Serializer):
    property_id = serializers.IntegerField(required=False, help_text="Sync a specific property only")
    start_date = serializers.DateField(required=False, help_text="Start date for calendar sync")
    end_date = serializers.DateField(required=False, help_text="End date for calendar sync")
