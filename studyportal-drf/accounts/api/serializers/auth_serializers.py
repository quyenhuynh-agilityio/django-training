"""
Authentication Serializers

Serializers for authentication-related operations:
- User registration
- Login
- Password reset (request and confirm)
- Change password
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .mixins import (
    PasswordConfirmationMixin,
    StripAndLowerEmailMixin,
    StripNameMixin,
    UIDAndTokenValidatorMixin,
)

User = get_user_model()


class UserRegistrationSerializer(
    StripAndLowerEmailMixin, StripNameMixin, PasswordConfirmationMixin, serializers.ModelSerializer
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
        validators=[validate_password],  # apply Django's password policy
        style={'input_type': 'password'},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
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

    # ---- Field-level validations ---------------------------------------------------------

    def validate_email(self, value):
        """
        Normalize and ensure email is unique.
        """
        value = self.normalize_email(value)
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists.')
        return value

    def validate_username(self, value):
        """
        Validate username:
        - Must contain only alphanumeric characters or underscores
        - Must be unique
        """
        value = value.strip()
        if not value.replace('_', '').isalnum():
            raise serializers.ValidationError(
                'Username may contain letters, numbers, and underscores only.'
            )
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists.')
        return value

    def validate_first_name(self, value):
        return self.clean_name(value, 'First name')

    def validate_last_name(self, value):
        return self.clean_name(value, 'Last name')

    # ---- Object-level validation ----------------------------------------------------------

    def validate(self, attrs):
        """
        Validate password confirmation.
        """
        self.validate_password_confirmation(attrs['password'], attrs['password_confirm'])
        return attrs

    # ---- Create User ---------------------------------------------------------------------

    def create(self, validated_data):
        """
        Create user account using Django's create_user() method,
        which automatically handles password hashing.

        Role is force-set to "student" for this serializer.
        """
        validated_data.pop('password_confirm')
        return User.objects.create_user(role='student', **validated_data)


class UserLoginSerializer(StripAndLowerEmailMixin, serializers.Serializer):
    """
    Authenticates user based on email + password.

    Important Security Note:
    ------------------------
    Never disclose which field (email or password) is incorrect.
    This prevents attackers from enumerating registered emails.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_email(self, value):
        return self.normalize_email(value)

    def validate(self, attrs):
        """
        Validate:
        - user exists
        - password matches
        - account is active
        """
        email = attrs['email']
        password = attrs['password']

        # Get user if exists, but quietly return generic message on failure
        user = User.objects.filter(email=email).first()

        if not user or not user.check_password(password):
            raise serializers.ValidationError({'detail': 'Invalid email or password.'})

        if not user.is_active:
            raise serializers.ValidationError({'detail': 'User account is disabled.'})

        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(StripAndLowerEmailMixin, serializers.Serializer):
    """
    Accepts an email for initiating password reset.

    Security Best Practice:
    -----------------------
    Do NOT check whether the email exists.
       API should always return success to prevent revealing registered emails.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        return self.normalize_email(value)


class PasswordResetConfirmSerializer(
    PasswordConfirmationMixin, UIDAndTokenValidatorMixin, serializers.Serializer
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

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )

    def validate(self, attrs):
        # Step 1: confirm new passwords match
        self.validate_password_confirmation(attrs['new_password'], attrs['new_password_confirm'])

        # Step 2–3: validate UID + token
        user = self.validate_uid_and_token(attrs['uid'], attrs['token'])

        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(PasswordConfirmationMixin, serializers.Serializer):
    """
    Allows already authenticated users to change their password.

    Validations:
    ------------
    - Old password required
    - New password must match confirmation
    - New password must NOT equal old password
    """

    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password], style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        # Confirm new passwords match
        self.validate_password_confirmation(attrs['new_password'], attrs['new_password_confirm'])

        # Ensure new password differs from old password
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {'new_password': 'New password must be different from the old password.'}
            )

        return attrs
