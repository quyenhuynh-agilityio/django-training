"""
Enrollment Model

Links students to courses with business rule validation.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.choices import CourseStatus, EnrollmentStatus, UserRole
from core.texts import ErrorMessage, HelpText


class Enrollment(models.Model):
    """
    Links a student to a course.
    Enforces: one active enrollment per student per course.
    """

    STATUS_ACTIVE = EnrollmentStatus.ACTIVE
    STATUS_COMPLETED = EnrollmentStatus.COMPLETED
    STATUS_DROPPED = EnrollmentStatus.DROPPED

    STATUS_CHOICES = EnrollmentStatus.choices

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
        limit_choices_to={'role': UserRole.STUDENT},
        help_text=HelpText.ENROLLMENT_STUDENT_FK,
    )

    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, related_name='enrollments'
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    is_active = models.BooleanField(default=True, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'enrollments'
        # One student can't be actively enrolled twice in same course
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'course'],
                condition=models.Q(is_active=True),
                name='unique_active_student_course',
            )
        ]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'is_active']),  # "My Courses" page
            models.Index(fields=['course', 'is_active']),  # Instructor roster
        ]

    def __str__(self):
        return f'{self.student.email} to {self.course.title}'

    def clean(self):
        """
        Validate enrollment rules.

        Only validates on NEW enrollments, not when updating existing ones
        or when the course is being modified.
        """
        # 1. Only students can enroll
        if self.student.role != UserRole.STUDENT:
            raise ValidationError(ErrorMessage.ONLY_STUDENTS_CAN_BE_ENROLLED)

        # 2. Only validate course enrollment rules for NEW enrollments
        # Skip validation if this is an existing enrollment being updated
        # Use _state.adding instead of checking pk, as UUID pk is set before save()
        if self._state.adding:  # Only for new enrollments
            # Course must be active
            if not self.course.is_active:
                raise ValidationError(ErrorMessage.COURSE_NOT_ACTIVE)

            # Course must have status='active' (not draft, in_progress, or completed)
            if self.course.status != CourseStatus.ACTIVE:
                raise ValidationError(ErrorMessage.COURSE_NOT_OPEN_FOR_ENROLLMENT)

            # Course must not be full
            if self.course.is_full:
                raise ValidationError(ErrorMessage.COURSE_REACHED_MAX_CAPACITY)

    def save(self, *args, **kwargs):  # noqa: DJ012
        # Only call full_clean on new instances to avoid validation issues
        # when course status changes
        # Use _state.adding instead of checking pk, as UUID pk is set before save()
        if self._state.adding:
            self.full_clean()
        super().save(*args, **kwargs)

    def unenroll(self):
        """
        Called when student leaves course.
        Used in: Student mobile app, API endpoint.
        """
        self.is_active = False
        self.status = EnrollmentStatus.DROPPED
        self.save(update_fields=['is_active', 'status', 'updated_at'])


__all__ = ['Enrollment']
