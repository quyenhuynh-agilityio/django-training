"""
Reusable validation & normalization utilities.

Design goals:
- No inheritance
- No DRF mixins
- Reusable across all apps
- Easy to test
"""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from core.texts import ErrorMessage

User = get_user_model()


def normalize_email(email):
    """
    Normalize email to lowercase and strip whitespace.

    Can be used in:
    - serializers
    - models
    - services
    - background tasks
    """
    if not email:
        return email
    return email.lower().strip()


# ─────────────────────────────────────────────────────────────
# Name validation
# ─────────────────────────────────────────────────────────────


def validate_name(value, field_name='Name'):
    """
    Validate and normalize a human name.

    Rules:
    - Cannot be empty
    - Letters, spaces, hyphens, apostrophes only
    - Proper capitalization
    """
    if not value or not value.strip():
        raise serializers.ValidationError(f'{field_name} cannot be empty.')

    value = value.strip()

    if not re.match(r"^[a-zA-Z\s'-]+$", value):
        raise serializers.ValidationError(
            f'{field_name} can only contain letters, spaces, hyphens, and apostrophes.'
        )

    return value.title()


# ─────────────────────────────────────────────────────────────
# Password confirmation
# ─────────────────────────────────────────────────────────────


def validate_password_confirmation(password, password_confirm):
    """
    Ensure password and password_confirm match.
    """
    if password != password_confirm:
        raise serializers.ValidationError({'password_confirm': ErrorMessage.PASSWORDS_DO_NOT_MATCH})


# ─────────────────────────────────────────────────────────────
# Password reset token
# ─────────────────────────────────────────────────────────────


def validate_reset_token(uid, token):
    """
    Validate password reset token and return user.

    Used for:
    - password reset
    - email verification
    - account recovery
    """
    try:
        uid_decoded = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=uid_decoded)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        raise serializers.ValidationError(  # noqa: B904
            {'uid': ErrorMessage.INVALID_RESET_LINK}
        )

    if not default_token_generator.check_token(user, token):
        raise serializers.ValidationError({'token': ErrorMessage.INVALID_OR_EXPIRED_RESET_TOKEN})

    if not user.is_active:
        raise serializers.ValidationError({'detail': ErrorMessage.USER_ACCOUNT_DISABLED})

    return user
