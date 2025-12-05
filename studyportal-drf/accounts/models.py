import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model — replaces Django's default User.
    Uses email as login (not username) + adds role system.
    Required for: Student registration, login, instructor management, admin dashboard.
    """

    # ─── Role System (RBAC) ─────────────────────────────────────
    ROLE_STUDENT = 'student'  # Can enroll in courses
    ROLE_INSTRUCTOR = 'instructor'  # Can create & manage courses
    ROLE_ADMIN = 'admin'  # Full access via Django admin

    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
        (ROLE_INSTRUCTOR, 'Instructor'),
        (ROLE_ADMIN, 'Admin'),
    ]

    # ─── Primary Key & Core Fields ──────────────────────────────
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Secure, unguessable ID used in APIs and mobile app',
    )

    email = models.EmailField(
        unique=True,
        blank=False,
        db_index=True,  # Critical: login queries use email
        help_text='Used as login identifier (not username)',
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT,
        db_index=True,  # Fast filtering: all instructors, all students
        help_text='Determines user permissions in the platform',
    )

    # Keep these for Django admin compatibility + full name display
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    # ─── Timestamps ─────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, help_text='When user registered')
    updated_at = models.DateTimeField(auto_now=True, help_text='Last profile update')

    # ─── Authentication Settings ────────────────────────────────
    USERNAME_FIELD = 'email'  # Login with email, not username
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']  # For createsuperuser

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        """
        Used in: Instructor dropdowns, student lists, profile display.
        Falls back to email prefix if names are empty.
        """
        if self.first_name or self.last_name:
            return f'{self.first_name} {self.last_name}'.strip()
        return self.email.split('@')[0]

    def is_student(self):
        """Check if user is a student"""
        return self.role == 'student'

    def is_instructor(self):
        """Check if user is an instructor"""
        return self.role == 'instructor'

    def is_admin_user(self):
        """Check if user is an admin"""
        return self.role == 'admin' or self.is_staff or self.is_superuser

    def clean(self):
        """Model-level validation"""
        super().clean()
        if self.email:
            self.email = self.email.lower()
