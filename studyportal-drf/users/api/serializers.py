"""
Updated Authentication Serializers for Simplified User Model

File: accounts/serializers.py

Changes:
- Removed EmailVerificationToken references
- Validation now uses User model methods
- Cleaner, simpler code
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from core.serializers import get_audit_read_only_fields
from core.texts import ErrorMessage, HelpText
from utils.validators import (
    normalize_email,
    validate_name,
    validate_password_confirmation,
    validate_reset_token,
)

User = get_user_model()


class UserRegistrationSerializer(
    serializers.ModelSerializer,
):
    """
    Handles new student registration.

    Features:
    ---------
    - Email normalization + uniqueness validation
    - Username sanitized and validated
    - Password confirmation
    - Strong password validation (via Django)
    - Creates account with role="student"
    """

    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text=HelpText.PASSWORD_STRENGTH_REQUIREMENTS,
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text=HelpText.MUST_MATCH_PASSWORD,
    )

    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())],
        required=True,
        help_text=HelpText.EMAIL_MUST_BE_UNIQUE,
    )
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all())],
        required=True,
        help_text=HelpText.USERNAME_UNIQUE_AND_FORMAT,
    )

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
            'password_confirm',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    # ─────────────────────────────────────────────────────
    # Field validation
    # ─────────────────────────────────────────────────────

    def validate_email(self, value):
        """Normalize email to lowercase"""
        return normalize_email(value)

    def validate_username(self, value):
        """Validate username format"""
        value = value.strip()
        if not value.replace('_', '').isalnum():
            raise serializers.ValidationError(ErrorMessage.USERNAME_INVALID_CHARS)
        return value

    def validate_first_name(self, value):
        """Validate and normalize first name"""
        return validate_name(value, 'First name')

    def validate_last_name(self, value):
        """Validate and normalize last name"""
        return validate_name(value, 'Last name')

    # ─────────────────────────────────────────────────────
    # Object-level validation
    # ─────────────────────────────────────────────────────

    def validate(self, attrs):
        """Validate password confirmation"""
        validate_password_confirmation(
            attrs['password'],
            attrs['password_confirm'],
        )
        return attrs

    # ─────────────────────────────────────────────────────
    # Create user
    # ─────────────────────────────────────────────────────

    def create(self, validated_data):
        """
        Create user with is_active=False and generate verification token.
        """
        validated_data.pop('password_confirm')
        user = User.objects.create_user(role='student', **validated_data)

        # Generate verification token
        user.generate_verification_token()

        return user


# ═══════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════


class UserLoginSerializer(serializers.Serializer):
    """Authenticates user based on email + password"""

    email = serializers.EmailField(help_text=HelpText.USER_EMAIL_ADDRESS)
    password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text=HelpText.USER_PASSWORD,
    )

    def validate_email(self, value):
        return normalize_email(value)

    def validate(self, attrs):
        """
        Validate user exists, password matches, and account is active
        """
        email = attrs['email']
        password = attrs['password']

        user = User.objects.filter(email=email).first()

        if not user or not user.check_password(password):
            raise serializers.ValidationError({'detail': ErrorMessage.INVALID_EMAIL_OR_PASSWORD})

        if not user.is_active:
            raise serializers.ValidationError({'detail': ErrorMessage.USER_ACCOUNT_DISABLED})

        attrs['user'] = user
        return attrs


# ═══════════════════════════════════════════════════════════════
# EMAIL VERIFICATION
# ═══════════════════════════════════════════════════════════════


class EmailVerificationSerializer(serializers.Serializer):
    """
    Validates email verification token.

    Much simpler now - just user_id and token!
    """

    user_id = serializers.UUIDField(help_text=HelpText.EMAIL_VERIFICATION_USER_ID)
    token = serializers.CharField(
        min_length=32,
        max_length=64,
        help_text=HelpText.EMAIL_VERIFICATION_TOKEN_FROM_EMAIL,
    )

    def validate(self, attrs):
        """Validate user_id and token"""
        user_id = attrs['user_id']
        token = attrs['token']

        # Get user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({'detail': ErrorMessage.INVALID_VERIFICATION_LINK})  # noqa: B904

        # Check if already verified
        if user.is_active:
            raise serializers.ValidationError({'detail': ErrorMessage.EMAIL_ALREADY_VERIFIED})

        # Validate token
        expiry_hours = getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24)

        if not user.is_verification_token_valid(token, expiry_hours):
            raise serializers.ValidationError(
                {'detail': ErrorMessage.INVALID_OR_EXPIRED_VERIFICATION_TOKEN}
            )

        attrs['user'] = user
        return attrs


class ResendVerificationSerializer(serializers.Serializer):
    """Request new verification email"""

    email = serializers.EmailField(help_text=HelpText.RESEND_VERIFICATION_EMAIL)

    def validate_email(self, value):
        return normalize_email(value)


# ═══════════════════════════════════════════════════════════════
# PASSWORD RESET
# ═══════════════════════════════════════════════════════════════


class PasswordResetRequestSerializer(serializers.Serializer):
    """Accepts an email for initiating password reset"""

    email = serializers.EmailField(help_text=HelpText.PASSWORD_RESET_EMAIL)

    def validate_email(self, value):
        return normalize_email(value)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Validates reset token and allows setting a new password"""

    uid = serializers.CharField(help_text=HelpText.RESET_UID)
    token = serializers.CharField(help_text=HelpText.RESET_TOKEN)
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text=HelpText.PASSWORD_STRENGTH_REQUIREMENTS,
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text=HelpText.MUST_MATCH_PASSWORD,
    )

    def validate(self, attrs):
        """Validate password reset request"""
        # Confirm passwords match
        validate_password_confirmation(
            attrs['new_password'],
            attrs['new_password_confirm'],
        )

        # Validate UID + token
        user = validate_reset_token(attrs['uid'], attrs['token'])
        attrs['user'] = user
        return attrs


# ═══════════════════════════════════════════════════════════════
# CHANGE PASSWORD
# ═══════════════════════════════════════════════════════════════


class ChangePasswordSerializer(serializers.Serializer):
    """Allows authenticated users to change their password"""

    old_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text=HelpText.CURRENT_PASSWORD,
    )
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text=HelpText.PASSWORD_STRENGTH_REQUIREMENTS,
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
        help_text=HelpText.MUST_MATCH_PASSWORD,
    )

    def validate_old_password(self, value):
        """Verify old password is correct"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(ErrorMessage.OLD_PASSWORD_INCORRECT)
        return value

    def validate(self, attrs):
        """Validate password change request"""
        # Confirm new passwords match
        validate_password_confirmation(
            attrs['new_password'],
            attrs['new_password_confirm'],
        )

        # New password must differ from old
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {'new_password': ErrorMessage.NEW_PASSWORD_MUST_DIFFER}
            )

        return attrs


# ═══════════════════════════════════════════════════════════════
# USER PROFILE
# ═══════════════════════════════════════════════════════════════


class UserProfileSerializer(serializers.ModelSerializer):
    """Returns full user profile details"""

    full_name = serializers.CharField(read_only=True)
    is_email_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'is_active',
            'is_email_verified',
            'email_verified_at',
            'date_joined',
            'created_at',
        ]
        read_only_fields = get_audit_read_only_fields(
            'email',
            'username',
            'role',
            'is_active',
            'is_email_verified',
            'email_verified_at',
            'date_joined',
            include_updated=False,
        )


# ═══════════════════════════════════════════════════════════════
# RESPONSE SERIALIZERS
# ═══════════════════════════════════════════════════════════════


class RegistrationResponseSerializer(serializers.Serializer):
    """Response for POST /auth/register/"""

    message = serializers.CharField()
    user = UserProfileSerializer(required=True)


class LoginResponseSerializer(serializers.Serializer):
    """Response for POST /auth/login/"""

    access_token = serializers.CharField(required=True, min_length=10)
    refresh_token = serializers.CharField(required=True, min_length=10)
    user = UserProfileSerializer(required=True)


class LogoutSuccessResponseSerializer(serializers.Serializer):
    """Response for POST /auth/logout/"""

    message = serializers.CharField()


class LogoutWithWarningResponseSerializer(serializers.Serializer):
    """Response for POST /auth/logout/ with warning"""

    message = serializers.CharField()
    warning = serializers.CharField()


class PasswordResetResponseSerializer(serializers.Serializer):
    """Response for POST /auth/password-reset/"""

    message = serializers.CharField()
    debug = serializers.DictField(required=False)


class MessageOnlyResponseSerializer(serializers.Serializer):
    """Generic success response"""

    message = serializers.CharField()


class MeResponseSerializer(serializers.Serializer):
    """Response for GET/PUT/PATCH /auth/me/"""

    user = UserProfileSerializer(required=True)


__all__ = [
    'UserRegistrationSerializer',
    'UserLoginSerializer',
    'EmailVerificationSerializer',
    'ResendVerificationSerializer',
    'PasswordResetRequestSerializer',
    'PasswordResetConfirmSerializer',
    'ChangePasswordSerializer',
    'UserProfileSerializer',
    'RegistrationResponseSerializer',
    'LoginResponseSerializer',
    'LogoutSuccessResponseSerializer',
    'LogoutWithWarningResponseSerializer',
    'PasswordResetResponseSerializer',
    'MessageOnlyResponseSerializer',
    'MeResponseSerializer',
]
