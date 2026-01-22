from django.db import models


class UserRole(models.TextChoices):
    STUDENT = 'student', 'Student'
    INSTRUCTOR = 'instructor', 'Instructor'
    ADMIN = 'admin', 'Admin'


class CourseStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'


class EnrollmentStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    COMPLETED = 'completed', 'Completed'
    DROPPED = 'dropped', 'Dropped'


class NotificationType:
    """Notification type constants"""

    STUDENT_ENROLLED = 'STUDENT_ENROLLED'
    STUDENT_REMOVED = 'STUDENT_REMOVED'
    COURSE_FULL = 'COURSE_FULL'

    CHOICES = [
        (STUDENT_ENROLLED, 'Student Enrolled'),
        (STUDENT_REMOVED, 'Student Removed'),
        (COURSE_FULL, 'Course Full'),
    ]


__all__ = ['UserRole', 'CourseStatus', 'EnrollmentStatus', 'NotificationType']
