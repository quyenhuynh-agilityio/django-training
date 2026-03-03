"""
Django Signals for User Model

Currently handles:
- Deactivating enrollments when user is disabled
"""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.sentry import sentry_capture_exception
from enrollments.models import Enrollment

User = get_user_model()


@receiver(post_save, sender=User)
def deactivate_enrollments_when_user_disabled(sender, instance, **kwargs):
    """
    Deactivate all enrollments when a user account is disabled.
    """
    try:
        if not instance.is_active:
            Enrollment.objects.filter(student=instance, is_active=True).update(is_active=False)
    except Exception as exc:  # pragma: no cover - defensive
        sentry_capture_exception(
            exc,
            tags={'signal': 'deactivate_enrollments_when_user_disabled', 'module': 'users'},
            contexts={'user': {'id': str(instance.pk)}},
        )
        raise
