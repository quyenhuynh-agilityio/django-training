import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.choices import CourseStatus, UserRole
from core.texts import ErrorMessage, HelpText


class Course(models.Model):
    """
    Core course model — now includes preview image and video for mobile app & course detail page.
    """

    # ─── Course Status Workflow ─────────────────────────────────
    STATUS_DRAFT = CourseStatus.DRAFT
    STATUS_ACTIVE = CourseStatus.ACTIVE
    STATUS_IN_PROGRESS = CourseStatus.IN_PROGRESS
    STATUS_COMPLETED = CourseStatus.COMPLETED

    STATUS_CHOICES = CourseStatus.choices

    # ─── Primary Key & Basic Info ───────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=255, help_text=HelpText.COURSE_TITLE)
    course_code = models.CharField(
        max_length=20,
        db_index=True,
        unique=True,
        help_text=HelpText.COURSE_CODE,
    )
    description = models.TextField(blank=True, help_text=HelpText.COURSE_DESCRIPTION)

    # ─── Media Fields (Used in Mobile App & Web) ─────────────────
    image_url = models.URLField(
        max_length=1000,
        blank=True,
        help_text=HelpText.COURSE_IMAGE_URL,
    )

    video_url = models.URLField(
        max_length=700,
        blank=True,
        help_text=HelpText.COURSE_VIDEO_URL,
    )

    # ─── Relationships ──────────────────────────────────────────
    categories = models.ManyToManyField(
        'categories.Category',
        related_name='courses',
        blank=True,
        help_text=HelpText.COURSE_CATEGORIES,
    )

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='taught_courses',
        limit_choices_to={'role': UserRole.INSTRUCTOR},
        help_text=HelpText.COURSE_INSTRUCTOR,
    )

    # ─── Status & Enrollment Control ────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
        help_text=HelpText.COURSE_STATUS,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=HelpText.COURSE_IS_ACTIVE,
    )

    max_students = models.PositiveIntegerField(
        null=True, blank=True, help_text=HelpText.COURSE_MAX_STUDENTS
    )

    # ─── Timestamps ─────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['course_code']),
            models.Index(fields=['status', 'is_active']),
        ]

    def __str__(self):
        return f'{self.course_code} - {self.title}'

    # ─── Helper Properties (Used in API, Templates, Mobile) ─────
    @property
    def _enrolled_count(self):
        """Current number of active students — used for capacity check (fallback when annotation not available)"""
        return self.enrollments.filter(is_active=True).count()

    @property
    def is_full(self):
        """True if enrollment cap is reached"""
        # Use annotated value if available, otherwise compute it
        enrolled = getattr(self, 'enrolled_count', self._enrolled_count)
        return self.max_students is not None and enrolled >= self.max_students

    def can_enroll(self):
        """
        Main enrollment rule used by mobile app and API.
        Students can only enroll if: active + status=active + not full
        """
        return self.is_active and self.status == self.STATUS_ACTIVE and not self.is_full

    # ─── Model Validation (Prevents Bad Data) ───────────────────
    def clean(self):
        # Only real instructors can be assigned
        if self.instructor and self.instructor.role != UserRole.INSTRUCTOR:
            raise ValidationError({'instructor': ErrorMessage.ONLY_INSTRUCTORS_CAN_TEACH})

        # Prevent disabling in-progress course with students
        if self.pk:
            try:
                old = Course.objects.only('status', 'is_active').get(pk=self.pk)
            except Course.DoesNotExist:
                old = None

            if old and old.is_active and not self.is_active:
                if old.status == self.STATUS_IN_PROGRESS and self._enrolled_count > 0:
                    raise ValidationError(ErrorMessage.CANNOT_DISABLE_IN_PROGRESS_WITH_STUDENTS)

    def save(self, *args, **kwargs):  # noqa: DJ012
        self.full_clean()
        super().save(*args, **kwargs)

    def soft_delete(self):
        """
        Soft delete the course by setting is_active to False.

        Raises:
            ValidationError: If the course is already deleted.
        """
        if not self.is_active:
            raise ValidationError(ErrorMessage.COURSE_ALREADY_DELETED)

        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
