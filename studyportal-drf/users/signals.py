from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from enrollments.models import Enrollment

User = get_user_model()


@receiver(post_save, sender=User)
def deactivate_enrollments_when_user_disabled(sender, instance, **kwargs):
    if not instance.is_active:
        Enrollment.objects.filter(student=instance, is_active=True).update(is_active=False)
