from rest_framework import serializers

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Base serializer for Notification model"""

    recipient_email = serializers.EmailField(source='recipient.email', read_only=True)
    recipient_name = serializers.CharField(source='recipient.full_name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'recipient',
            'recipient_email',
            'recipient_name',
            'type',
            'type_display',
            'payload',
            'is_read',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'recipient',
            'type',
            'payload',
            'created_at',
            'updated_at',
        ]


# ─── Response Serializers ───────────────────────────────────────────────────


class NotificationListResponseSerializer(serializers.Serializer):
    """Response serializer for paginated notification list"""

    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = NotificationSerializer(many=True)


class NotificationDetailResponseSerializer(serializers.Serializer):
    """Response serializer for single notification detail"""

    id = serializers.UUIDField()
    recipient = serializers.UUIDField()
    recipient_email = serializers.EmailField()
    recipient_name = serializers.CharField()
    type = serializers.CharField()
    type_display = serializers.CharField()
    payload = serializers.JSONField()
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class MarkAsReadResponseSerializer(serializers.Serializer):
    """Response serializer for mark as read action"""

    message = serializers.CharField()
    data = NotificationSerializer()


class MarkAllAsReadResponseSerializer(serializers.Serializer):
    """Response serializer for mark all as read action"""

    message = serializers.CharField()
    count = serializers.IntegerField()


class UnreadCountResponseSerializer(serializers.Serializer):
    """Response serializer for unread count"""

    unread_count = serializers.IntegerField()
