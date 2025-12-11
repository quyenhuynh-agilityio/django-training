"""
Account API Views

This package provides views for authentication and user profile operations.

Structure:
    - auth_views.py: Authentication-related views (registration, login, password reset)
"""

from .auth_views import (
    ChangePasswordView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    TokenRefreshSchemaView,
    UserLoginView,
    UserLogoutView,
    UserProfileView,
    UserRegistrationView,
)

__all__ = [
    'UserRegistrationView',
    'UserLoginView',
    'UserLogoutView',
    'PasswordResetRequestView',
    'PasswordResetConfirmView',
    'ChangePasswordView',
    'UserProfileView',
    'TokenRefreshSchemaView',
]
