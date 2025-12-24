"""
Authentication Serializers

Serializers for authentication-related operations:
- User registration
- Login
- Password reset (request and confirm)
- Change password
- User profile
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from core.serializers import (
    get_audit_read_only_fields,
)
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
        Create user account using Django's create_user() method,
        which automatically handles password hashing.

        Role is force-set to "student" for this serializer.
        """
        validated_data.pop('password_confirm')
        return User.objects.create_user(role='student', **validated_data)


# ─────────────────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────────────────


class UserLoginSerializer(
    serializers.Serializer,
):
    """
    Authenticates user based on email + password.

    Important Security Note:
    ------------------------
    Never disclose which field (email or password) is incorrect.
    This prevents attackers from enumerating registered emails.
    """

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
        Validate:
        - user exists
        - password matches
        - account is active
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


# ─────────────────────────────────────────────────────────────
# Password reset request
# ─────────────────────────────────────────────────────────────


class PasswordResetRequestSerializer(
    serializers.Serializer,
):
    """
    Accepts an email for initiating password reset.

    Security Best Practice:
    -----------------------
    Do NOT check whether the email exists.
    API should always return success to prevent revealing registered emails.
    """

    email = serializers.EmailField(help_text=HelpText.PASSWORD_RESET_EMAIL)

    def validate_email(self, value):
        return normalize_email(value)


# ─────────────────────────────────────────────────────────────
# Password reset confirm
# ─────────────────────────────────────────────────────────────


class PasswordResetConfirmSerializer(
    serializers.Serializer,
):
    """
    Validates reset token and allows setting a new password.

    Steps:
    ------
    1. Ensure new passwords match
    2. Decode UID and validate user
    3. Validate reset token
    4. Return user for view to update password
    """

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
        """Validate password reset request

        Steps:
        1. Check password confirmation match
        2. Validate UID and token
        3. Return user for password update
        """
        # 1. Confirm passwords match
        validate_password_confirmation(
            attrs['new_password'],
            attrs['new_password_confirm'],
        )

        # 2. Validate UID + token and return user
        user = validate_reset_token(attrs['uid'], attrs['token'])
        attrs['user'] = user
        return attrs


# ─────────────────────────────────────────────────────────────
# Change password
# ─────────────────────────────────────────────────────────────


class ChangePasswordSerializer(
    serializers.Serializer,
):
    """
    Allows already authenticated users to change their password.

    Validations:
    ------------
    - Old password required and must be correct
    - New password must match confirmation
    - New password must NOT equal old password
    """

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
        """
        Critical: Verify that the provided old password is correct.
        """
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

        # New password must be different from old
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {'new_password': ErrorMessage.NEW_PASSWORD_MUST_DIFFER}
            )

        return attrs


# ─────────────────────────────────────────────────────────────
# User profile
# ─────────────────────────────────────────────────────────────


class UserProfileSerializer(
    serializers.ModelSerializer,
):
    """
    Returns full user profile details.

    All sensitive fields are read-only to avoid unintended data exposure.
    """

    full_name = serializers.CharField(read_only=True)

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
            'date_joined',
            'created_at',
        ]
        read_only_fields = get_audit_read_only_fields(
            'email',
            'username',
            'role',
            'is_active',
            'date_joined',
            include_updated=False,
        )


__all__ = [
    'UserRegistrationSerializer',
    'UserLoginSerializer',
    'PasswordResetRequestSerializer',
    'PasswordResetConfirmSerializer',
    'ChangePasswordSerializer',
    'UserProfileSerializer',
]
