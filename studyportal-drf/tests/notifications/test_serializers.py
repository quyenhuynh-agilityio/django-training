"""Tests for notification API serializers."""

import pytest

from core.choices import NotificationType
from notifications.api.serializers import (
    MarkAllAsReadResponseSerializer,
    MarkAsReadResponseSerializer,
    NotificationSerializer,
    UnreadCountResponseSerializer,
)

pytestmark = pytest.mark.django_db


class TestNotificationSerializer:
    """Tests for NotificationSerializer."""

    def test_serializes_notification_with_recipient_fields(self, create_notification):
        notification = create_notification(
            payload={'course_code': 'CS101', 'message': 'Enrolled'},
            notification_type=NotificationType.STUDENT_ENROLLED,
        )
        serializer = NotificationSerializer(notification)
        data = serializer.data
        assert data['id'] == str(notification.id)
        assert data['type'] == NotificationType.STUDENT_ENROLLED
        assert data['type_display'] == 'Student Enrolled'
        assert data['payload'] == {'course_code': 'CS101', 'message': 'Enrolled'}
        assert data['is_read'] is False
        assert 'recipient_email' in data
        assert data['recipient_email'] == notification.recipient.email
        assert 'recipient_name' in data
        assert 'created_at' in data
        assert 'updated_at' in data

    def test_read_only_fields_include_id_and_recipient(self):
        """NotificationSerializer has id and recipient as read-only."""
        assert 'id' in NotificationSerializer.Meta.read_only_fields
        assert 'recipient' in NotificationSerializer.Meta.read_only_fields


class TestMarkAsReadResponseSerializer:
    """Tests for MarkAsReadResponseSerializer."""

    def test_serializes_message_and_data(self, create_notification):
        notification = create_notification()
        response_data = {'message': 'Notification marked as read', 'data': notification}
        serializer = MarkAsReadResponseSerializer(response_data)
        data = serializer.data
        assert data['message'] == 'Notification marked as read'
        assert 'data' in data
        assert data['data']['id'] == str(notification.id)


class TestMarkAllAsReadResponseSerializer:
    """Tests for MarkAllAsReadResponseSerializer."""

    def test_serializes_message_and_count(self):
        serializer = MarkAllAsReadResponseSerializer(
            data={'message': 'Marked 5 notification(s) as read', 'count': 5}
        )
        assert serializer.is_valid()
        data = serializer.validated_data
        assert data['message'] == 'Marked 5 notification(s) as read'
        assert data['count'] == 5


class TestUnreadCountResponseSerializer:
    """Tests for UnreadCountResponseSerializer."""

    def test_serializes_unread_count(self):
        serializer = UnreadCountResponseSerializer(data={'unread_count': 42})
        assert serializer.is_valid()
        assert serializer.validated_data['unread_count'] == 42
