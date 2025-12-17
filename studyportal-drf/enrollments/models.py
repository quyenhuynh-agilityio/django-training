"""
Enrollment Model

Links students to courses with business rule validation.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from courses.models import Course


class Enrollment(models.Model):
    """
    Links a student to a course.
    Enforces: one active enrollment per student per course.
    """

    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_DROPPED = 'dropped'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_DROPPED, 'Dropped'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
        limit_choices_to={'role': 'student'},
        help_text='Only student-role users can be enrolled',
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
        if self.student.role != 'student':
            raise ValidationError('Only students can be enrolled in courses.')

        # 2. Only validate course enrollment rules for NEW enrollments
        # Skip validation if this is an existing enrollment being updated
        if not self.pk:  # Only for new enrollments
            # Course must be active
            if not self.course.is_active:
                raise ValidationError('This course is not active.')

            # Course must have status='active' (not draft, in_progress, or completed)
            if self.course.status != Course.STATUS_ACTIVE:
                raise ValidationError(
                    'This course is not open for enrollment. '
                    'Only courses with "Active" status accept new enrollments.'
                )

            # Course must not be full
            if self.course.is_full:
                raise ValidationError('This course has reached maximum capacity.')

    def save(self, *args, **kwargs):  # noqa: DJ012
        # Only call full_clean on new instances to avoid validation issues
        # when course status changes
        if not self.pk:
            self.full_clean()
        super().save(*args, **kwargs)

    def unenroll(self):
        """
        Called when student leaves course.
        Used in: Student mobile app, API endpoint.
        """
        self.is_active = False
        self.status = self.STATUS_DROPPED
        self.save(update_fields=['is_active', 'status', 'updated_at'])


__all__ = ['Enrollment']
