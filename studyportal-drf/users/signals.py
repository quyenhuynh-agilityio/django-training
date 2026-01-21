"""
Django Signals for User Model

Handles:
- Sending verification email on registration
- Sending welcome email when user becomes active (email verified)
- Auto-enrolling students in introduction courses
- Deactivating enrollments when user is disabled
"""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from enrollments.models import Enrollment

from .tasks import (
    auto_enroll_intro_courses,
    send_welcome_email,
)

User = get_user_model()


# Store old instance state to detect transitions
_old_user_state = {}


@receiver(pre_save, sender=User)
def store_user_state_before_save(sender, instance, **kwargs):
    """
    Store the previous state of the user before save to detect transitions.
    """
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            _old_user_state[instance.pk] = {
                'is_active': old_instance.is_active,
                'email_verified_at': old_instance.email_verified_at,
            }
        except User.DoesNotExist:
            _old_user_state[instance.pk] = {
                'is_active': False,
                'email_verified_at': None,
            }


@receiver(post_save, sender=User)
def deactivate_enrollments_when_user_disabled(sender, instance, **kwargs):
    """
    Deactivate all enrollments when a user account is disabled.
    """
    if not instance.is_active:
        Enrollment.objects.filter(student=instance, is_active=True).update(is_active=False)


@receiver(post_save, sender=User)
def handle_user_email_verification(sender, instance, created, **kwargs):
    """
    Handle email verification and welcome flow via signals.

    When a user becomes active (email verified):
    1. Send welcome email asynchronously
    2. Auto-enroll student in introduction courses

    This ensures welcome email is sent even if verification happens
    outside the normal API flow.
    """
    # Check if user just became active (email verified)
    if instance.is_active and instance.email_verified_at:
        # Get old state to detect transition
        old_state = _old_user_state.get(instance.pk, {})
        was_inactive = not old_state.get('is_active', True)
        was_unverified = old_state.get('email_verified_at') is None

        # Only trigger if user transitioned from inactive/unverified to active/verified
        if was_inactive or was_unverified:
            # User just verified email - send welcome email
            send_welcome_email.delay(user_id=str(instance.id))

            # Auto-enroll students in introduction courses
            if instance.is_student:
                auto_enroll_intro_courses.delay(user_id=str(instance.id))

    # Clean up stored state
    if instance.pk in _old_user_state:
        del _old_user_state[instance.pk]
