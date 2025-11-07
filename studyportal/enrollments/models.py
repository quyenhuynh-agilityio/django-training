import uuid
from django.db import models
from django.conf import settings
from courses.models import Course


class Enrollment(models.Model):
    """
    Connects a user to a course (1:N relationships)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "course")
        ordering = ["-enrolled_at"]

    def __str__(self):
        return f"{self.user.username}  and {self.course.title}"
