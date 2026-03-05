"""Tests for Notification model."""

from unittest.mock import patch

import pytest

from core.choices import NotificationType
from notifications.models import Notification

pytestmark = pytest.mark.django_db


class TestNotificationModel:
    """Tests for Notification model."""

    def test_str_representation(self, create_user, create_notification):
        recipient = create_user(email='jane@example.com', first_name='Jane', last_name='Doe')
        notification = create_notification(recipient=recipient, notification_type=NotificationType.STUDENT_ENROLLED)
        assert str(notification) == 'STUDENT_ENROLLED for jane@example.com'

    def test_mark_as_read_updates_is_read_and_saves(self, create_notification):
        notification = create_notification(is_read=False)
        notification.mark_as_read()
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_mark_as_read_when_already_read_does_not_raise(self, create_notification):
        notification = create_notification(is_read=True)
        notification.mark_as_read()
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_mark_as_read_invalidates_cache(self, create_notification):
        notification = create_notification(is_read=False)
        with patch('django.core.cache.cache') as mock_cache:
            notification.mark_as_read()
            mock_cache.delete.assert_called_once()
            call_args = mock_cache.delete.call_args[0][0]
            assert 'notification_unread_count' in call_args
            assert str(notification.recipient_id) in call_args

    @patch('notifications.models.cache_get_or_set')
    def test_get_unread_count_cached_returns_cached_value(self, mock_cache_get_or_set, create_user):
        mock_cache_get_or_set.return_value = 3
        user = create_user()
        count = Notification.get_unread_count_cached(user.id)
        assert count == 3
        mock_cache_get_or_set.assert_called_once()
        call_kwargs = mock_cache_get_or_set.call_args[1]
        assert call_kwargs['timeout'] == 60

    def test_get_unread_count_cached_computes_count_when_cache_miss(
        self, create_user, create_notification
    ):
        user = create_user()
        create_notification(recipient=user, is_read=False)
        create_notification(recipient=user, is_read=False)
        create_notification(recipient=user, is_read=True)
        with patch('notifications.models.cache_get_or_set') as mock_cache_get_or_set:
            def call_loader(key, default, timeout):
                return default()
            mock_cache_get_or_set.side_effect = call_loader
            count = Notification.get_unread_count_cached(user.id)
        assert count == 2

    @patch('notifications.models.get_timeout')
    def test_get_unread_count_cached_uses_settings_timeout(self, mock_get_timeout, create_user):
        mock_get_timeout.return_value = 120
        with patch('notifications.models.cache_get_or_set') as mock_cache_get_or_set:
            mock_cache_get_or_set.return_value = 0
            Notification.get_unread_count_cached(create_user().id)
            mock_get_timeout.assert_called_with('NOTIFICATION_CACHE_TIMEOUT', 60)
