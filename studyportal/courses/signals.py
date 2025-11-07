from django.db.models.signals import post_save
from django.dispatch import receiver
from courses.models import Course
from enrollments.models import Enrollment


@receiver(post_save, sender=Course)
def deactivate_enrollments_when_course_disabled(sender, instance, **kwargs):
    if not instance.is_active:
        Enrollment.objects.filter(course=instance, is_active=True).update(
            is_active=False
        )
