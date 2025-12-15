"""
Account Serializer Validation Utilities

Reusable validation utilities for account/authentication serializers:
- Email normalization
- Name validation
- Password confirmation
- UID and token validation

Note: These are validation utilities, not DRF mixins (which provide view behavior).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

User = get_user_model()


class EmailNormalization:
    """
    Provides email normalization for serializers.

    Usage:
        class MySerializer(EmailNormalization, serializers.Serializer):
            def validate_email(self, value):
                return self.normalize_email(value)
    """

    @staticmethod
    def normalize_email(value: str) -> str:
        """
        Normalize email input:
        - Removes leading/trailing whitespace
        - Converts to lowercase
        """
        return value.strip().lower()


class NameValidation:
    """
    Provides name validation for serializers.

    Usage:
        class MySerializer(NameValidation, serializers.Serializer):
            def validate_first_name(self, value):
                return self.validate_name(value, 'First name')
    """

    @staticmethod
    def validate_name(value: str, field_name: str) -> str:
        """
        Normalize and validate name fields.

        Args:
            value: The name value to validate
            field_name: Display name for error messages (e.g., 'First name')

        Returns:
            Stripped name value

        Raises:
            serializers.ValidationError: If name is empty after stripping
        """
        value = value.strip()
        if not value:
            raise serializers.ValidationError(f'{field_name} cannot be empty.')
        return value


class PasswordConfirmation:
    """
    Provides password confirmation validation for serializers.

    Usage:
        class MySerializer(PasswordConfirmation, serializers.Serializer):
            def validate(self, attrs):
                self.check_password_match(
                    attrs['password'],
                    attrs['password_confirm']
                )
                return attrs
    """

    @staticmethod
    def check_password_match(password: str, password_confirm: str) -> None:
        """
        Verify that password and confirmation match.

        Args:
            password: The password value
            password_confirm: The confirmation password value

        Raises:
            serializers.ValidationError: If passwords don't match
        """
        if password != password_confirm:
            raise serializers.ValidationError({'password_confirm': "Password fields didn't match."})


class ResetTokenValidation:
    """
    Provides password reset token validation for serializers.

    Usage:
        class PasswordResetConfirmSerializer(ResetTokenValidation, serializers.Serializer):
            def validate(self, attrs):
                user = self.validate_reset_token(attrs['uid'], attrs['token'])
                attrs['user'] = user
                return attrs
    """

    @staticmethod
    def validate_reset_token(uid: str, token: str):
        """
        Validate password reset UID and token pair.

        Args:
            uid: Base64-encoded user ID
            token: Password reset token

        Returns:
            User object if validation succeeds

        Raises:
            serializers.ValidationError: If UID/token is invalid or expired
        """
        try:
            uid_decoded = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid_decoded)
        except Exception:
            # Generic error to prevent information leakage
            raise serializers.ValidationError({'detail': 'Invalid reset link.'}) from None

        # Validate token authenticity and expiration
        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError({'detail': 'Invalid or expired reset token.'})

        return user
