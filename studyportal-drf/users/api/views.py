"""
Authentication API ViewSet

Combines all authentication endpoints into a single ViewSet.
Uses custom actions for each endpoint with proper response handling.
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
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
from core.texts import ErrorMessage, SuccessMessage

from .serializers import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)

User = get_user_model()


class AuthViewSet(CommonViewSet):
    """
    Authentication and User Profile API

    Provides endpoints for user registration, authentication, password management,
    and profile operations. Uses JWT (JSON Web Tokens) for authentication.

    **Authentication Endpoints:**
    - Register: Create new user account
    - Login: Authenticate and receive JWT tokens
    - Logout: Invalidate refresh token
    - Password Reset: Request and confirm password resets
    - Password Change: Change password for authenticated users

    **Profile Endpoints:**
    - Me: View and update user profile

    **Token Usage:**
    For protected endpoints, include the access token in the Authorization header:
    ```
    Authorization: Bearer <your_access_token>
    ```
    """

    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]

    serializer_action_classes = {
        'register': UserRegistrationSerializer,
        'login': UserLoginSerializer,
        'logout': None,
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

    @extend_schema(
        summary='Register a new user account',
        description="""
        Create a new user account with email and password.

        **Registration Flow:**
        1. Submit email, password, and user details
        2. System validates the data and creates account
        3. User can immediately login with credentials

        **Note:** Email addresses must be unique across the system.
        """,
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                response=UserRegistrationSerializer,
                description='User account created successfully',
                examples=[
                    OpenApiExample(
                        name='Successful Registration',
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
                description='Bad Request - Validation failed',
                examples=[
                    OpenApiExample(
                        name='Email Already Exists',
                        value={'email': ['A user with this email address already exists.']},
                    ),
                    OpenApiExample(
                        name='Weak Password',
                        value={
                            'password': [
                                'This password is too short. It must contain at least 8 characters.'
                            ]
                        },
                    ),
                    OpenApiExample(
                        name='Missing Required Fields',
                        value={
                            'email': ['This field is required.'],
                            'password': ['This field is required.'],
                        },
                    ),
                ],
            ),
        },
        tags=['Authentication'],
    )
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
        user_data = UserProfileSerializer(user).data

        return self.created(
            {
                'message': SuccessMessage.REGISTRATION_SUCCESS,
                'user': user_data,
            }
        )

    # ============================================
    # USER LOGIN
    # ============================================

    @extend_schema(
        summary='Login to your account',
        description="""
        Authenticate with email and password to receive JWT tokens.

        **Authentication Flow:**
        1. Submit email and password
        2. Receive access token (short-lived) and refresh token (long-lived)
        3. Include access token in `Authorization: Bearer <token>` header for protected endpoints
        4. Use refresh token to get new access token when expired

        **Token Lifetimes:**
        - Access Token: Valid for 1 hour
        - Refresh Token: Valid for 7 days
        """,
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(
                description='Login successful - Returns JWT tokens',
                examples=[
                    OpenApiExample(
                        name='Successful Login',
                        value={
                            'message': 'Login successful',
                            'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                            'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
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
                description='Bad Request - Invalid credentials',
                examples=[
                    OpenApiExample(
                        name='Invalid Credentials',
                        value={
                            'message': 'Login failed',
                            'errors': {'detail': 'Invalid email or password.'},
                        },
                    ),
                    OpenApiExample(
                        name='Missing Fields',
                        value={
                            'email': ['This field is required.'],
                            'password': ['This field is required.'],
                        },
                    ),
                ],
            ),
            401: OpenApiResponse(
                description='Unauthorized - Account inactive',
                examples=[
                    OpenApiExample(
                        name='Inactive Account',
                        value={'detail': 'User account is disabled.'},
                    )
                ],
            ),
        },
        tags=['Authentication'],
    )
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

        # Use serializer for consistent user data formatting
        user_data = UserProfileSerializer(user).data

        return self.ok(
            {
                'message': SuccessMessage.LOGIN_SUCCESS,
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': user_data,
            }
        )

    # ============================================
    # USER LOGOUT
    # ============================================

    @extend_schema(
        summary='Logout from your account',
        description="""
        Invalidate the refresh token to logout.

        **Logout Behavior:**
        - Refresh token is blacklisted and cannot be reused
        - Access token remains valid until natural expiration
        - For complete security, client should also delete stored tokens

        **Security Note:** Requires `rest_framework_simplejwt.token_blacklist`
        in INSTALLED_APPS for token blacklisting.
        """,
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'refresh': {
                        'type': 'string',
                        'description': 'The refresh token to blacklist',
                        'example': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    }
                },
                'required': ['refresh'],
            }
        },
        responses={
            200: OpenApiResponse(
                description='Logout successful',
                examples=[
                    OpenApiExample(name='Success', value={'message': 'Logout successful'}),
                    OpenApiExample(
                        name='Success (No Blacklist)',
                        value={
                            'message': 'Logout successful',
                            'warning': 'Token blacklist not enabled. Add rest_framework_simplejwt.token_blacklist to INSTALLED_APPS.',
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(
                description='Bad Request - Invalid or missing token',
                examples=[
                    OpenApiExample(
                        name='Invalid Token',
                        value={'message': 'Logout failed', 'error': 'Token is invalid or expired'},
                    ),
                    OpenApiExample(
                        name='Missing Token',
                        value={
                            'message': 'Logout failed',
                            'code': {'refresh': ['This field is required.']},
                        },
                    ),
                ],
            ),
            401: OpenApiResponse(
                description='Unauthorized - Authentication required',
                examples=[
                    OpenApiExample(
                        name='Not Authenticated',
                        value={'detail': 'Authentication credentials were not provided.'},
                    )
                ],
            ),
        },
        tags=['Authentication'],
    )
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
                message=ErrorMessage.LOGOUT_FAILED,
                code={'refresh': ['This field is required.']},
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except AttributeError:
            return self.ok(
                {
                    'message': SuccessMessage.LOGOUT_SUCCESS,
                    'warning': (
                        'Token blacklist not enabled. '
                        'Add rest_framework_simplejwt.token_blacklist to INSTALLED_APPS.'
                    ),
                }
            )
        except TokenError:
            return self.bad_request(
                message=ErrorMessage.LOGOUT_FAILED,
                code={'refresh': ['Token is invalid or expired']},
            )

        return self.ok({'message': SuccessMessage.LOGOUT_SUCCESS})

    # ============================================
    # PASSWORD RESET REQUEST
    # ============================================

    @extend_schema(
        summary='Request a password reset link',
        description="""
        Send a password reset link to the user's email address.

        **Reset Flow:**
        1. Submit email address
        2. If account exists, reset link is sent to email
        3. Link contains UID and token valid for 24 hours
        4. Use link to access password reset confirmation page

        **Security Features:**
        - Returns success even if email doesn't exist (prevents email enumeration)
        - Token is single-use and expires after 24 hours
        - Original password remains valid until reset is completed

        **Development Mode:**
        When `DEBUG=True` or `PASSWORD_RESET_DEBUG_EXPOSE_TOKENS=True`,
        the response includes the reset token and link for testing purposes.
        """,
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                description='Password reset email sent (or would be sent)',
                examples=[
                    OpenApiExample(
                        name='Production Response',
                        value={
                            'message': 'If an account exists with this email, a password reset link has been sent.',
                        },
                    ),
                    OpenApiExample(
                        name='Development Response',
                        value={
                            'message': 'If an account exists with this email, a password reset link has been sent.',
                            'debug': {
                                'uid': 'MQ',
                                'token': 'abc123-token',
                                'reset_link': 'http://localhost:3000/reset-password/MQ/abc123-token/',
                            },
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(
                description='Bad Request - Invalid email format',
                examples=[
                    OpenApiExample(
                        name='Invalid Email',
                        value={
                            'message': 'Invalid email format',
                            'code': {'email': ['Enter a valid email address.']},
                        },
                    )
                ],
            ),
        },
        tags=['Authentication'],
    )
    @action(detail=False, methods=['post'], url_path='password-reset')
    def password_reset(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        debug_payload = None

        try:
            user = User.objects.get(email=email, is_active=True)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/reset-password/{uid}/{token}/"

            # Send email
            if not getattr(settings, 'PASSWORD_RESET_DISABLE_EMAIL', False):
                send_mail(
                    'Password Reset Request',
                    f'Click here to reset your password:\n\n{reset_link}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                )

            # Optional debug info
            if getattr(settings, 'PASSWORD_RESET_DEBUG_EXPOSE_TOKENS', settings.DEBUG):
                debug_payload = {'uid': uid, 'token': token, 'reset_link': reset_link}

        except User.DoesNotExist:
            pass  # Always return success (prevent email enumeration)

        response = {'message': SuccessMessage.PASSWORD_RESET_EMAIL_SENT}
        if debug_payload:
            response['debug'] = debug_payload
        return self.ok(response)

    # ============================================
    # PASSWORD RESET CONFIRMATION
    # ============================================

    @extend_schema(
        summary='Complete password reset with token',
        description="""
        Reset password using the token received via email.

        **Reset Confirmation Flow:**
        1. Extract UID and token from reset link
        2. Submit new password with UID and token
        3. Password is updated and user can login with new credentials

        **Token Validation:**
        - Token must be valid and not expired (24-hour limit)
        - Token can only be used once
        - User account must be active

        **After Reset:**
        - Old password is no longer valid
        - User can immediately login with new password
        - All existing sessions remain active (tokens not invalidated)
        """,
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(
                description='Password reset completed successfully',
                examples=[
                    OpenApiExample(
                        name='Success',
                        value={
                            'message': 'Password has been reset successfully. You can now login with your new password.'
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description='Bad Request - Invalid token or validation errors',
                examples=[
                    OpenApiExample(
                        name='Invalid Token',
                        value={
                            'message': 'Password reset failed',
                            'errors': {'detail': 'Invalid or expired reset token.'},
                        },
                    ),
                    OpenApiExample(
                        name='Weak Password',
                        value={
                            'new_password': [
                                'This password is too short. It must contain at least 8 characters.'
                            ]
                        },
                    ),
                    OpenApiExample(
                        name='Missing Fields',
                        value={
                            'uid': ['This field is required.'],
                            'token': ['This field is required.'],
                            'new_password': ['This field is required.'],
                        },
                    ),
                ],
            ),
        },
        tags=['Authentication'],
    )
    @action(detail=False, methods=['post'], url_path='password-reset-confirm')
    def password_reset_confirm(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        new_password = serializer.validated_data['new_password']

        # Set new password
        user.set_password(new_password)
        user.save(update_fields=['password'])

        return self.ok({'message': SuccessMessage.PASSWORD_RESET_SUCCESS})

    # ============================================
    # CHANGE PASSWORD (AUTHENTICATED)
    # ============================================

    @extend_schema(
        summary='Change your current password',
        description="""
        Change password for the authenticated user.

        **Change Password Flow:**
        1. Provide current password for verification
        2. Submit new password
        3. Password is updated immediately

        **Security Notes:**
        - Must provide correct old password
        - User remains logged in (JWT tokens remain valid)
        - Recommended to logout other sessions after password change

        **Password Requirements:**
        - Minimum 8 characters
        - Cannot be entirely numeric
        - Cannot be too similar to personal information
        """,
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(
                description='Password changed successfully',
                examples=[
                    OpenApiExample(
                        name='Success', value={'message': 'Password changed successfully'}
                    )
                ],
            ),
            400: OpenApiResponse(
                description='Bad Request - Validation errors',
                examples=[
                    OpenApiExample(
                        name='Wrong Old Password',
                        value={
                            'message': 'Password change failed',
                            'errors': {'old_password': ['Wrong password.']},
                        },
                    ),
                    OpenApiExample(
                        name='Weak New Password',
                        value={
                            'new_password': [
                                'This password is too short. It must contain at least 8 characters.'
                            ]
                        },
                    ),
                    OpenApiExample(
                        name='Missing Fields',
                        value={
                            'old_password': ['This field is required.'],
                            'new_password': ['This field is required.'],
                        },
                    ),
                ],
            ),
            401: OpenApiResponse(
                description='Unauthorized - Authentication required',
                examples=[
                    OpenApiExample(
                        name='Not Authenticated',
                        value={'detail': 'Authentication credentials were not provided.'},
                    )
                ],
            ),
        },
        tags=['Authentication'],
    )
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
        new_password = serializer.validated_data['new_password']

        user.set_password(new_password)
        user.save(update_fields=['password'])

        return self.ok({'message': SuccessMessage.PASSWORD_CHANGED_SUCCESS})

    # ============================================
    # USER PROFILE
    # ============================================

    @extend_schema(
        summary='Get or update your profile',
        description="""
        Retrieve or update the authenticated user's profile information.

        **HTTP Methods:**
        - `GET`: Retrieve current user profile
        - `PUT`: Full profile update (all fields required)
        - `PATCH`: Partial profile update (only changed fields)

        **Updatable Fields:**
        - first_name
        - last_name

        **Read-Only Fields:**
        - id
        - email
        - username
        - role
        - date_joined

        **Note:** To change email or password, use dedicated endpoints.
        """,
        request=UserProfileSerializer,
        responses={
            200: OpenApiResponse(
                response=UserProfileSerializer,
                description='Profile retrieved or updated successfully',
                examples=[
                    OpenApiExample(
                        name='Profile Data',
                        value={
                            'id': '123e4567-e89b-12d3-a456-426614174000',
                            'email': 'student@example.com',
                            'username': 'student123',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'full_name': 'John Doe',
                            'role': 'student',
                            'date_joined': '2024-01-15T10:30:00Z',
                        },
                    )
                ],
            ),
            400: OpenApiResponse(
                description='Bad Request - Validation errors',
                examples=[
                    OpenApiExample(
                        name='Invalid Field', value={'first_name': ['This field may not be blank.']}
                    )
                ],
            ),
            401: OpenApiResponse(
                description='Unauthorized - Authentication required',
                examples=[
                    OpenApiExample(
                        name='Not Authenticated',
                        value={'detail': 'Authentication credentials were not provided.'},
                    )
                ],
            ),
        },
        tags=['User Profile'],
    )
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
            return self.ok(self.get_serializer(user).data)

        serializer = self.get_serializer(
            user,
            data=request.data,
            partial=(request.method == 'PATCH'),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return self.ok(serializer.data)


__all__ = ['AuthViewSet']
