"""
Account Serializer Mixins

Reusable mixins for account/authentication serializers providing:
- Email normalization
- Name validation
- Password confirmation
- UID and token validation
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

User = get_user_model()


class StripAndLowerEmailMixin:
    """
    Normalize email input:
    - Removes leading/trailing whitespace
    - Converts to lowercase

    Used in: Registration, Login, Password Reset (request)
    """

    def normalize_email(self, value: str) -> str:
        return value.strip().lower()


class StripNameMixin:
    """
    Normalize first/last names + ensure non-empty.

    Reusable for any serializer dealing with names.
    """

    def clean_name(self, value: str, field_name: str):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(f'{field_name} cannot be empty.')
        return value


class PasswordConfirmationMixin:
    """
    Shared logic for verifying password_confirmation fields.

    Reduces duplication across:
    - Registration
    - Password Reset Confirm
    - Change Password
    """

    def validate_password_confirmation(self, password, password_confirm):
        if password != password_confirm:
            raise serializers.ValidationError("Password fields didn't match.")


class UIDAndTokenValidatorMixin:
    """
    Validates password reset UID + token pair.

    Used exclusively in password reset confirmation phase.
    Ensures:
    - UID decodes properly
    - User exists for given UID
    - Token is valid and not expired
    """

    def validate_uid_and_token(self, uid, token):
        try:
            uid_decoded = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid_decoded)
        except Exception:
            # Prevent leakage of specific error detail
            raise serializers.ValidationError('Invalid reset link.')  # noqa: B904

        # Validate token authenticity and expiration
        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError('Invalid or expired reset token.')

        return user
