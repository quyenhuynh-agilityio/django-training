import logging
import uuid

from django.conf import settings
from django.db import models

from core.cache import build_cache_key, cache_get_or_set, get_timeout
from core.choices import NotificationType
from core.texts import HelpText

logger = logging.getLogger(__name__)


class Notification(models.Model):
    """
    Notification model for enrollment events.
    Supports caching and async creation via Celery.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True,
        help_text=HelpText.NOTIFICATION_RECIPIENT,
    )

    type = models.CharField(
        max_length=50,
        choices=NotificationType.CHOICES,
        db_index=True,
        help_text=HelpText.NOTIFICATION_TYPE,
    )

    payload = models.JSONField(default=dict, help_text=HelpText.NOTIFICATION_PAYLOAD)

    is_read = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['type', 'recipient']),
        ]

    def __str__(self):
        return f'{self.type} for {self.recipient.email}'

    def mark_as_read(self):
        """Mark notification as read and invalidate cache"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read', 'updated_at'])

            # Clear user's unread count cache
            from django.core.cache import cache

            cache_key = build_cache_key('notification_unread_count', user_id=self.recipient_id)
            cache.delete(cache_key)

    @classmethod
    def get_unread_count_cached(cls, user_id):
        """
        Get cached unread notification count for user.
        Cache timeout: 60 seconds (configurable via settings).
        """
        cache_key = build_cache_key('notification_unread_count', user_id=user_id)
        timeout = get_timeout('NOTIFICATION_CACHE_TIMEOUT', 60)

        return cache_get_or_set(
            cache_key,
            lambda: cls.objects.filter(recipient_id=user_id, is_read=False).count(),
            timeout=timeout,
        )
