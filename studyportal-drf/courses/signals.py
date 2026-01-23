from django.db.models.signals import post_save
from django.dispatch import receiver

from core.sentry import sentry_capture_exception
from courses.models import Course
from enrollments.models import Enrollment


@receiver(post_save, sender=Course)
def deactivate_enrollments_when_course_disabled(sender, instance, **kwargs):
    try:
        if not instance.is_active:
            Enrollment.objects.filter(course=instance, is_active=True).update(is_active=False)
    except Exception as exc:  # pragma: no cover - defensive
        sentry_capture_exception(
            exc,
            tags={'signal': 'deactivate_enrollments_when_course_disabled', 'module': 'courses'},
            contexts={'course': {'id': str(instance.pk)}},
        )
        raise
