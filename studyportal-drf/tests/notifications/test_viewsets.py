"""Tests for NotificationViewSet API."""

import pytest
from unittest.mock import patch

from rest_framework import status

from core.choices import NotificationType
from notifications.models import Notification

pytestmark = pytest.mark.django_db


def test_notification_list_requires_authentication(api_client, create_notification):
    """List notifications returns 401 when not authenticated."""
    response = api_client.get('/api/v1/notifications/')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_notification_list_returns_only_own_notifications(
    api_client, create_user, create_notification
):
    """Authenticated user sees only their notifications."""
    user = create_user(email='owner@example.com', username='owner')
    other = create_user(email='other@example.com', username='other')
    create_notification(recipient=user)
    create_notification(recipient=user)
    create_notification(recipient=other)

    api_client.force_authenticate(user=user)
    response = api_client.get('/api/v1/notifications/')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['count'] == 2
    assert len(response.data['results']) == 2


def test_notification_list_filter_by_is_read(
    api_client, create_user, create_notification
):
    """Filter notifications by is_read."""
    user = create_user()
    create_notification(recipient=user, is_read=False)
    create_notification(recipient=user, is_read=True)
    create_notification(recipient=user, is_read=False)

    api_client.force_authenticate(user=user)
    response = api_client.get('/api/v1/notifications/?is_read=false')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['count'] == 2
    for item in response.data['results']:
        assert item['is_read'] is False


def test_notification_list_filter_by_type(
    api_client, create_user, create_notification
):
    """Filter notifications by type."""
    user = create_user()
    create_notification(recipient=user, notification_type=NotificationType.STUDENT_ENROLLED)
    create_notification(recipient=user, notification_type=NotificationType.STUDENT_REMOVED)
    create_notification(recipient=user, notification_type=NotificationType.STUDENT_ENROLLED)

    api_client.force_authenticate(user=user)
    response = api_client.get('/api/v1/notifications/?type=STUDENT_ENROLLED')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['count'] == 2
    for item in response.data['results']:
        assert item['type'] == NotificationType.STUDENT_ENROLLED


def test_notification_retrieve_own(api_client, create_user, create_notification):
    """User can retrieve their own notification."""
    user = create_user()
    notification = create_notification(recipient=user)

    api_client.force_authenticate(user=user)
    response = api_client.get(f'/api/v1/notifications/{notification.id}/')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['id'] == str(notification.id)
    assert response.data['recipient_email'] == user.email


def test_notification_retrieve_other_returns_404(
    api_client, create_user, create_notification
):
    """User cannot retrieve another user's notification."""
    owner = create_user(email='owner@example.com', username='owner')
    other = create_user(email='other@example.com', username='other')
    notification = create_notification(recipient=owner)

    api_client.force_authenticate(user=other)
    response = api_client.get(f'/api/v1/notifications/{notification.id}/')

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_notification_mark_as_read(api_client, create_user, create_notification):
    """User can mark their notification as read."""
    user = create_user()
    notification = create_notification(recipient=user, is_read=False)

    api_client.force_authenticate(user=user)
    response = api_client.post(f'/api/v1/notifications/{notification.id}/mark_as_read/')

    assert response.status_code == status.HTTP_200_OK
    assert 'marked as read' in response.data['message']
    notification.refresh_from_db()
    assert notification.is_read is True


def test_notification_mark_as_read_other_returns_404(
    api_client, create_user, create_notification
):
    """User cannot mark another user's notification as read."""
    owner = create_user(email='owner@example.com', username='owner')
    other = create_user(email='other@example.com', username='other')
    notification = create_notification(recipient=owner)

    api_client.force_authenticate(user=other)
    response = api_client.post(f'/api/v1/notifications/{notification.id}/mark_as_read/')

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_notification_mark_all_as_read(
    api_client, create_user, create_notification
):
    """User can mark all their notifications as read."""
    user = create_user()
    create_notification(recipient=user, is_read=False)
    create_notification(recipient=user, is_read=False)
    create_notification(recipient=user, is_read=True)

    api_client.force_authenticate(user=user)
    response = api_client.post('/api/v1/notifications/mark_all_as_read/')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['count'] == 2
    assert '2 notification(s)' in response.data['message']
    unread = Notification.objects.filter(recipient=user, is_read=False).count()
    assert unread == 0


def test_notification_mark_all_as_read_clears_cache(
    api_client, create_user, create_notification
):
    """mark_all_as_read invalidates unread count cache."""
    user = create_user()
    create_notification(recipient=user, is_read=False)

    api_client.force_authenticate(user=user)
    with patch('django.core.cache.cache') as mock_cache:
        response = api_client.post('/api/v1/notifications/mark_all_as_read/')
    assert response.status_code == status.HTTP_200_OK
    mock_cache.delete.assert_called_once()


def test_notification_unread_count(api_client, create_user, create_notification):
    """Unread count returns correct count."""
    user = create_user()
    create_notification(recipient=user, is_read=False)
    create_notification(recipient=user, is_read=False)
    create_notification(recipient=user, is_read=True)

    api_client.force_authenticate(user=user)
    with patch.object(Notification, 'get_unread_count_cached', return_value=2):
        response = api_client.get('/api/v1/notifications/unread_count/')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['unread_count'] == 2


def test_notification_unread_count_requires_auth(api_client):
    """Unread count requires authentication."""
    response = api_client.get('/api/v1/notifications/unread_count/')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_notification_swagger_fake_view_returns_empty_queryset(create_user):
    """When swagger_fake_view is set, get_queryset returns empty."""
    from rest_framework.request import Request
    from rest_framework.test import APIRequestFactory

    from notifications.api.views import NotificationViewSet

    user = create_user()
    factory = APIRequestFactory()
    request = Request(factory.get('/api/v1/notifications/'))
    request.user = user

    viewset = NotificationViewSet()
    viewset.swagger_fake_view = True
    viewset.request = request

    queryset = viewset.get_queryset()
    assert queryset.count() == 0
