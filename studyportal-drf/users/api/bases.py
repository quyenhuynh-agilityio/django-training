"""
Authentication Serializer Base Classes

Reusable base classes for authentication serializers.
These are NOT DRF mixins - they're standard Python base classes.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from core.texts import ErrorMessage

User = get_user_model()


class EmailNormalizationBase(serializers.Serializer):
    """
    Base class providing email normalization.

    Ensures emails are lowercase and stripped of whitespace.

    Usage:
        class MySerializer(EmailNormalizationBase, serializers.ModelSerializer):
            def validate_email(self, value):
                return self.normalize_email(value)
    """

    def normalize_email(self, email):
        """
        Normalize email to lowercase and strip whitespace.

        Args:
            email: Raw email string

        Returns:
            Normalized email string
        """
        if not email:
            return email
        return email.lower().strip()


class NameValidationBase(serializers.Serializer):
    """
    Base class providing name field validation.

    Validates that names:
    - Are not empty after stripping
    - Contain only letters, spaces, hyphens, and apostrophes
    - Are properly capitalized

    Usage:
        class MySerializer(NameValidationBase, serializers.ModelSerializer):
            def validate_first_name(self, value):
                return self.validate_name(value, 'First name')
    """

    def validate_name(self, value, field_name='Name'):
        """
        Validate and normalize a name field.

        Args:
            value: Raw name string
            field_name: Name of the field for error messages

        Returns:
            Validated and normalized name

        Raises:
            ValidationError: If name format is invalid
        """
        if not value or not value.strip():
            raise serializers.ValidationError(f'{field_name} cannot be empty.')

        value = value.strip()

        # Allow letters, spaces, hyphens, and apostrophes
        # Examples: Mary-Jane, O'Connor, Anne Marie
        import re

        if not re.match(r"^[a-zA-Z\s'-]+$", value):
            raise serializers.ValidationError(
                f'{field_name} can only contain letters, spaces, hyphens, and apostrophes.'
            )

        # Capitalize properly (Mary-jane -> Mary-Jane)
        return value.title()


class PasswordConfirmationBase(serializers.Serializer):
    """
    Base class providing password confirmation validation.

    Ensures that password and password_confirm fields match.

    Usage:
        class MySerializer(PasswordConfirmationBase, serializers.Serializer):
            password = serializers.CharField(...)
            password_confirm = serializers.CharField(...)

            def validate(self, attrs):
                self.check_password_match(attrs['password'], attrs['password_confirm'])
                return attrs
    """

    def check_password_match(self, password, password_confirm):
        """
        Validate that password and confirmation match.

        Args:
            password: Password string
            password_confirm: Confirmation password string

        Raises:
            ValidationError: If passwords don't match
        """
        if password != password_confirm:
            raise serializers.ValidationError(
                {'password_confirm': ErrorMessage.PASSWORDS_DO_NOT_MATCH}
            )


class ResetTokenValidationBase(serializers.Serializer):
    """
    Base class providing password reset token validation.

    Validates UID and token for password reset operations.

    Usage:
        class MySerializer(ResetTokenValidationBase, serializers.Serializer):
            uid = serializers.CharField()
            token = serializers.CharField()

            def validate(self, attrs):
                user = self.validate_reset_token(attrs['uid'], attrs['token'])
                attrs['user'] = user
                return attrs
    """

    def validate_reset_token(self, uid, token):
        """
        Validate password reset token and return user.

        Args:
            uid: Base64 encoded user ID
            token: Password reset token

        Returns:
            User instance if valid

        Raises:
            ValidationError: If UID or token is invalid
        """
        # Decode UID
        try:
            uid_decoded = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid_decoded)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({'uid': ErrorMessage.INVALID_RESET_LINK})  # noqa: B904

        # Validate token
        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError(
                {'token': ErrorMessage.INVALID_OR_EXPIRED_RESET_TOKEN}
            )

        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError({'detail': ErrorMessage.USER_ACCOUNT_DISABLED})

        return user


__all__ = [
    'EmailNormalizationBase',
    'NameValidationBase',
    'PasswordConfirmationBase',
    'ResetTokenValidationBase',
]
