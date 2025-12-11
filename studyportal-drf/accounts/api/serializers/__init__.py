"""
Account API Serializers

This package provides serializers for User/Auth operations following Django REST Framework
best practices with a mixin-based architecture for code reusability.

Structure:
    - mixins.py: Reusable serializer components (mixins)
    - auth_serializers.py: Authentication-related serializers (registration, login, password reset)
    - profile_serializers.py: User profile serializers
"""

# Import mixins
# Import auth serializers
from .auth_serializers import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
)
from .mixins import (
    PasswordConfirmationMixin,
    StripAndLowerEmailMixin,
    StripNameMixin,
    UIDAndTokenValidatorMixin,
)

# Import profile serializers
from .profile_serializers import UserProfileSerializer

__all__ = [
    # Mixins
    'StripAndLowerEmailMixin',
    'StripNameMixin',
    'PasswordConfirmationMixin',
    'UIDAndTokenValidatorMixin',
    # Auth Serializers
    'UserRegistrationSerializer',
    'UserLoginSerializer',
    'PasswordResetRequestSerializer',
    'PasswordResetConfirmSerializer',
    'ChangePasswordSerializer',
    # Profile Serializers
    'UserProfileSerializer',
]
