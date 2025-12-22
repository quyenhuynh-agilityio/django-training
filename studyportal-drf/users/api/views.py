"""
Authentication API ViewSet

Combines all authentication endpoints into a single ViewSet.
Uses custom actions for each endpoint with proper response handling.
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import permissions
from rest_framework.decorators import action

from core.api_views import CommonViewSet

from .serializers import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)

User = get_user_model()


@extend_schema_view(
    register=extend_schema(
        summary='Register new student',
        description='Create a new student account with email and password',
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                description='User registered successfully',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'message': 'Registration successful. Please login.',
                            'user': {
                                'id': '123e4567-e89b-12d3-a456-426614174000',
                                'email': 'student@example.com',
                                'username': 'student123',
                                'first_name': 'John',
                                'last_name': 'Doe',
                                'role': 'student',
                            },
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description='Validation errors',
                examples=[
                    OpenApiExample(
                        'Email exists',
                        value={'email': ['A user with this email address already exists.']},
                    ),
                ],
            ),
        },
        tags=['Authentication'],
    ),
    login=extend_schema(
        summary='User login',
        description='Authenticate user with email and password, returns JWT tokens',
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(
                description='Login successful',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'message': 'Login successful',
                            'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                            'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGc...',
                            'user': {
                                'id': '123e4567-e89b-12d3-a456-426614174000',
                                'email': 'student@example.com',
                                'username': 'student123',
                                'full_name': 'John Doe',
                                'role': 'student',
                            },
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description='Invalid credentials',
                examples=[
                    OpenApiExample(
                        'Invalid credentials',
                        value={
                            'message': 'Login failed',
                            'errors': {'detail': 'Invalid email or password.'},
                        },
                    )
                ],
            ),
        },
        tags=['Authentication'],
    ),
    logout=extend_schema(
        summary='User logout',
        description='Blacklist refresh token to logout user',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'refresh': {'type': 'string', 'description': 'Refresh token to blacklist'}
                },
                'required': ['refresh'],
            }
        },
        responses={
            200: OpenApiResponse(
                description='Logout successful',
                examples=[OpenApiExample('Success', value={'message': 'Logout successful'})],
            ),
            400: OpenApiResponse(
                description='Invalid token',
                examples=[
                    OpenApiExample(
                        'Invalid token',
                        value={'message': 'Logout failed', 'error': 'Token is invalid or expired'},
                    )
                ],
            ),
        },
        tags=['Authentication'],
    ),
    password_reset=extend_schema(
        summary='Request password reset',
        description=(
            'Generate a password reset token. In DEBUG or when '
            '`PASSWORD_RESET_DEBUG_EXPOSE_TOKENS` is True, the response also '
            'includes the `uid`, `token`, and `reset_link` for testing.'
        ),
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                description='Reset email sent or token generated',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'message': 'If an account exists with this email, a password reset link has been sent.',
                            'debug': {
                                'uid': 'MQ',
                                'token': 'abc123-token',
                                'reset_link': 'http://localhost:3000/reset-password/MQ/abc123-token/',
                            },
                        },
                    )
                ],
            )
        },
        tags=['Authentication'],
    ),
    password_reset_confirm=extend_schema(
        summary='Confirm password reset',
        description='Reset password using token from email',
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(
                description='Password reset successful',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'message': 'Password has been reset successfully. You can now login with your new password.'
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description='Invalid token or validation errors',
                examples=[
                    OpenApiExample(
                        'Invalid token',
                        value={
                            'message': 'Password reset failed',
                            'errors': {'detail': 'Invalid or expired reset token.'},
                        },
                    )
                ],
            ),
        },
        tags=['Authentication'],
    ),
    password_change=extend_schema(
        summary='Change password',
        description='Change password for authenticated user',
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(
                description='Password changed successfully',
                examples=[
                    OpenApiExample('Success', value={'message': 'Password changed successfully'})
                ],
            ),
            400: OpenApiResponse(
                description='Validation errors',
                examples=[
                    OpenApiExample(
                        'Wrong password',
                        value={
                            'message': 'Password change failed',
                            'errors': {'old_password': ['Wrong password.']},
                        },
                    )
                ],
            ),
        },
        tags=['Authentication'],
    ),
    me=extend_schema(
        summary='Get/update current user profile',
        description="Get or update authenticated user's profile",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
        tags=['Profile'],
    ),
)
class AuthViewSet(CommonViewSet):
    """
    Authentication API ViewSet

    All endpoints are custom actions - no default CRUD operations.
    Inherits from CommonViewSet for consistent response formatting.

    Routes:
    - POST   /auth/register/              -> register()
    - POST   /auth/login/                 -> login()
    - POST   /auth/logout/                -> logout()
    - POST   /auth/password-reset/        -> password_reset()
    - POST   /auth/password-reset-confirm/ -> password_reset_confirm()
    - POST   /auth/password-change/       -> password_change()
    - GET    /auth/me/                    -> me()
    - PUT    /auth/me/                    -> me()
    - PATCH  /auth/me/                    -> me()
    """

    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]  # Default, overridden per action

    # Map actions to their serializers
    serializer_action_classes = {
        'register': UserRegistrationSerializer,
        'login': UserLoginSerializer,
        'logout': None,  # No input serializer needed
        'password_reset': PasswordResetRequestSerializer,
        'password_reset_confirm': PasswordResetConfirmSerializer,
        'password_change': ChangePasswordSerializer,
        'me': UserProfileSerializer,
    }

    def get_serializer_class(self):
        """Return appropriate serializer for each action"""
        return self.serializer_action_classes.get(self.action, UserRegistrationSerializer)

    def get_permissions(self):
        """
        Public endpoints: register, login, password_reset, password_reset_confirm
        Protected endpoints: logout, password_change, me
        """
        if self.action in ['logout', 'password_change', 'me']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    # ============================================
    # USER REGISTRATION
    # ============================================

    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register new user (student or instructor)

        Creates a new user account with hashed password.
        Returns user data without password.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return self.created(
            {
                'message': 'Registration successful. Please login.',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                },
            }
        )

    # ============================================
    # USER LOGIN
    # ============================================

    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Login with email and password

        Authenticates users and generates JWT access and refresh tokens.
        Works for all roles (student, instructor, admin).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return self.ok(
            {
                'message': 'Login successful',
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role,
                },
            }
        )

    # ============================================
    # USER LOGOUT
    # ============================================

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        Logout current user

        Blacklists the refresh token to prevent reuse.
        Access token remains valid until natural expiration.

        Note: Requires 'rest_framework_simplejwt.token_blacklist' in INSTALLED_APPS
        """
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return self.bad_request(
                message='Logout failed', code={'refresh': ['This field is required.']}
            )

        try:
            token = RefreshToken(refresh_token)
        except TokenError:
            return self.bad_request(
                message='Logout failed', code={'refresh': ['Token is invalid or expired']}
            )

        try:
            token.blacklist()
        except AttributeError:
            # Blacklist app not installed - just return success
            # In production, you should install token_blacklist
            return self.ok(
                {
                    'message': 'Logout successful',
                    'warning': 'Token blacklist not enabled. Add rest_framework_simplejwt.token_blacklist to INSTALLED_APPS.',
                }
            )
        except TokenError:
            return self.bad_request(
                message='Logout failed', code={'refresh': ['Token is invalid or expired']}
            )

        return self.ok({'message': 'Logout successful'})

    # ============================================
    # PASSWORD RESET REQUEST
    # ============================================

    @action(detail=False, methods=['post'], url_path='password-reset')
    def password_reset(self, request):
        """
        Request password reset email

        Sends password reset link to user's email.
        Token valid for 24 hours.
        Always returns success to prevent email enumeration.
        """
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return self.bad_request(message='Invalid email format', code=serializer.errors)

        email = serializer.validated_data['email']
        debug_payload = None

        try:
            user = User.objects.get(email=email, is_active=True)

            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Build reset link
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_link = f'{frontend_url}/reset-password/{uid}/{token}/'

            # Debug payload for testing
            debug_expose = getattr(settings, 'PASSWORD_RESET_DEBUG_EXPOSE_TOKENS', settings.DEBUG)
            if debug_expose:
                debug_payload = {'uid': uid, 'token': token, 'reset_link': reset_link}

            # Send email (optional in dev)
            send_email = not getattr(settings, 'PASSWORD_RESET_DISABLE_EMAIL', False)
            if send_email:
                try:
                    send_mail(
                        subject='Password Reset Request',
                        message=(
                            f'Click the link below to reset your password:\n\n'
                            f'{reset_link}\n\n'
                            f'This link will expire in 24 hours.'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception as email_error:
                    print(f'Email error: {email_error}')

        except User.DoesNotExist:
            # Don't reveal if email exists
            pass

        response_payload = {
            'message': 'If an account exists with this email, a password reset link has been sent.'
        }

        if debug_payload:
            response_payload['debug'] = debug_payload

        return self.ok(response_payload)

    # ============================================
    # PASSWORD RESET CONFIRMATION
    # ============================================

    @action(detail=False, methods=['post'], url_path='password-reset-confirm')
    def password_reset_confirm(self, request):
        """
        Confirm password reset with token

        Validates reset token from email and sets new password.
        Token is single-use and expires after 24 hours.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        new_password = serializer.validated_data['new_password']

        # Set new password
        user.set_password(new_password)
        user.save()

        return self.ok(
            {
                'message': 'Password has been reset successfully. You can now login with your new password.'
            }
        )

    # ============================================
    # CHANGE PASSWORD (AUTHENTICATED)
    # ============================================

    @action(detail=False, methods=['post'], url_path='password-change')
    def password_change(self, request):
        """
        Change password for authenticated user

        Validates old password before changing to new password.
        User remains logged in (JWT token still valid).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        # Verify old password
        if not user.check_password(old_password):
            return self.bad_request(
                message='Password change failed', code={'old_password': ['Wrong password.']}
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        return self.ok({'message': 'Password changed successfully'})

    # ============================================
    # USER PROFILE
    # ============================================

    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """
        Get or update current user profile

        GET: Returns current user data
        PUT: Full profile update (all fields)
        PATCH: Partial profile update (any fields)

        Updatable fields: first_name, last_name
        Read-only fields: email, username, role
        """
        user = request.user

        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return self.ok(serializer.data)

        # PUT or PATCH
        serializer = self.get_serializer(
            user, data=request.data, partial=(request.method == 'PATCH')
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.ok(serializer.data)


__all__ = ['AuthViewSet']
