import secrets
import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from core.choices import UserRole
from core.texts import HelpText

# ═══════════════════════════════════════════════════════════════
# MANAGER FOR COMMON QUERIES
# ═══════════════════════════════════════════════════════════════


class User(AbstractUser):
    """
    Custom User model with built-in email verification.

    Email Verification Flow:
    1. User registers → is_active=False, verification_token generated
    2. Token sent via email
    3. User clicks link → token validated → is_active=True
    4. Token cleared after successful verification
    """

    # ─── Role System (RBAC) ─────────────────────────────────────
    ROLE_STUDENT = UserRole.STUDENT  # Can enroll in courses
    ROLE_INSTRUCTOR = UserRole.INSTRUCTOR  # Can create & manage courses
    ROLE_ADMIN = UserRole.ADMIN  # Full access via Django admin

    ROLE_CHOICES = UserRole.choices

    # ─── Primary Key & Core Fields ──────────────────────────────
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=HelpText.USER_ID,
    )

    is_active = models.BooleanField(
        default=False,  # Requires email verification
        help_text=HelpText.USER_STATUS,
    )

    email = models.EmailField(
        unique=True,
        blank=False,
        db_index=True,
        help_text=HelpText.USER_EMAIL_LOGIN,
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STUDENT,
        db_index=True,  # Fast filtering: all instructors, all students
        help_text=HelpText.USER_ROLE,
    )

    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    # ─── Email Verification Fields ──────────────────────────────
    email_verification_token = models.CharField(  # noqa: DJ001
        max_length=64,
        blank=True,
        null=True,  # allow clearing token after verification
        db_index=True,  # Fast token lookups
        help_text=HelpText.EMAIL_VERIFICATION_TOKEN,
    )

    email_verification_token_created = models.DateTimeField(
        blank=True,
        null=True,
        help_text=HelpText.EMAIL_VERIFICATION_TOKEN_CREATED,
    )

    email_verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=HelpText.EMAIL_VERIFIED_AT,
    )

    # ─── Timestamps ─────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True, help_text=HelpText.USER_CREATED_AT)
    updated_at = models.DateTimeField(auto_now=True, help_text=HelpText.USER_UPDATED_AT)

    # ─── Authentication Settings ────────────────────────────────
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email_verification_token'], name='user_verify_token_idx'),
            models.Index(fields=['is_active', 'email'], name='user_active_email_idx'),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        """Full name or email prefix fallback"""
        if self.first_name or self.last_name:
            return f'{self.first_name} {self.last_name}'.strip()
        return self.email.split('@')[0]

    @property
    def is_student(self):
        """Check if user is a student"""
        return self.role == self.ROLE_STUDENT

    @property
    def is_instructor(self):
        """Check if user is an instructor"""
        return self.role == self.ROLE_INSTRUCTOR

    @property
    def is_email_verified(self):
        """Check if email has been verified"""
        return self.email_verified_at is not None

    def clean(self):
        """Model-level validation"""
        super().clean()
        if self.email:
            self.email = self.email.lower()

    # ═══════════════════════════════════════════════════════════
    # EMAIL VERIFICATION METHODS
    # ═══════════════════════════════════════════════════════════

    def generate_verification_token(self):
        """
        Generate a new verification token for this user.

        Returns:
            str: The generated token
        """
        self.email_verification_token = secrets.token_urlsafe(48)
        self.email_verification_token_created = timezone.now()
        self.save(update_fields=['email_verification_token', 'email_verification_token_created'])
        return self.email_verification_token

    def is_verification_token_valid(self, token, expiry_hours=24):
        """
        Check if the provided verification token is valid.

        Args:
            token: Token to validate
            expiry_hours: Hours until token expires (default: 24)

        Returns:
            bool: True if token is valid, False otherwise
        """
        # Token must match
        if not self.email_verification_token or self.email_verification_token != token:
            return False

        # Token must not be expired
        if not self.email_verification_token_created:
            return False

        expiry_time = self.email_verification_token_created + timedelta(hours=expiry_hours)
        if timezone.now() > expiry_time:
            return False

        return True

    def verify_email(self):
        """
        Mark email as verified and activate account.
        Clears the verification token.
        """
        self.is_active = True
        self.email_verified_at = timezone.now()
        self.email_verification_token = None
        self.email_verification_token_created = None
        self.save(
            update_fields=[
                'is_active',
                'email_verified_at',
                'email_verification_token',
                'email_verification_token_created',
            ]
        )

    def clear_verification_token(self):
        """Clear verification token (e.g., when generating a new one)"""
        self.email_verification_token = None
        self.email_verification_token_created = None
        self.save(update_fields=['email_verification_token', 'email_verification_token_created'])
