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


__all__ = ['UserRole', 'CourseStatus', 'EnrollmentStatus']
