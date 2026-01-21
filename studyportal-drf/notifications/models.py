import uuid

from django.conf import settings
from django.db import models

from core.texts import HelpText


class Notification(models.Model):
    """
    Advanced Notification model using JSON payload for dynamic content.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The user receiving the alert
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text=HelpText.NOTIFICATION_RECIPIENT,  # Defined in your texts file
    )

    # Categorization (e.g., 'ENROLLMENT', 'COURSE_FULL', 'SYSTEM_MAINTENANCE')
    type = models.CharField(max_length=50, db_index=True, help_text=HelpText.NOTIFICATION_TYPE)

    # Dynamic data (e.g., {"course_id": "...", "course_name": "...", "actor": "..."})
    payload = models.JSONField(default=dict, help_text=HelpText.NOTIFICATION_PAYLOAD)

    is_read = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.type} for {self.recipient.email}'
