from drf_spectacular.utils import extend_schema

from django.contrib.auth import get_user_model
from rest_framework import permissions, viewsets
from rest_framework.decorators import action

from .serializers import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)
from .views import (
    ChangePasswordView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    UserLoginView,
    UserLogoutView,
    UserProfileView,
    UserRegistrationView,
)


class AuthViewSet(viewsets.GenericViewSet):
    """
    Router-based Authentication API
    Wraps existing view logic into ViewSet actions.
    """

    # Provide serializers for schema generation & router inspection
    queryset = get_user_model().objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    serializer_action_classes = {
        'register': UserRegistrationSerializer,
        'login': UserLoginSerializer,
        'logout': UserLoginSerializer,
        'password_reset': PasswordResetRequestSerializer,
        'password_reset_confirm': PasswordResetConfirmSerializer,
        'password_change': ChangePasswordSerializer,
        'me': UserProfileSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_action_classes.get(self.action, self.serializer_class)

    @extend_schema(tags=['Authentication'], summary='Register new user')
    @action(detail=False, methods=['post'])
    def register(self, request):
        return UserRegistrationView.as_view()(request._request)

    @extend_schema(tags=['Authentication'], summary='User login')
    @action(detail=False, methods=['post'])
    def login(self, request):
        return UserLoginView.as_view()(request._request)

    @extend_schema(tags=['Authentication'], summary='User logout')
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        return UserLogoutView.as_view()(request._request)

    @extend_schema(tags=['Authentication'], summary='Request password reset')
    @action(detail=False, methods=['post'])
    def password_reset(self, request):
        return PasswordResetRequestView.as_view()(request._request)

    @extend_schema(tags=['Authentication'], summary='Confirm password reset')
    @action(detail=False, methods=['post'])
    def password_reset_confirm(self, request):
        return PasswordResetConfirmView.as_view()(request._request)

    @extend_schema(tags=['Authentication'], summary='Change password')
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def password_change(self, request):
        return ChangePasswordView.as_view()(request._request)

    @extend_schema(tags=['Authentication'], summary='Get/update current user profile')
    @action(
        detail=False,
        methods=['get', 'put', 'patch'],
        permission_classes=[permissions.IsAuthenticated],
    )
    def me(self, request):
        return UserProfileView.as_view()(request._request)


__all__ = ['AuthViewSet']
