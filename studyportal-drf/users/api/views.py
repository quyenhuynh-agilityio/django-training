"""
Updated Authentication ViewSet for Simplified User Model

File: accounts/views.py

Key improvements:
- No separate EmailVerificationToken queries
- Simpler, more intuitive code
- Fewer database queries
- Better performance
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
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import permissions
from rest_framework.decorators import action

from core.api_views import CommonViewSet
from core.texts import ErrorMessage, SuccessMessage

# Import Celery tasks
from users.tasks import (
    send_password_reset_confirmation_email,
    send_password_reset_email,
    send_verification_email,
)

from .serializers import (
    ChangePasswordSerializer,
    EmailVerificationSerializer,
    LoginResponseSerializer,
    LogoutSuccessResponseSerializer,
    LogoutWithWarningResponseSerializer,
    MeResponseSerializer,
    MessageOnlyResponseSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetResponseSerializer,
    RegistrationResponseSerializer,
    ResendVerificationSerializer,
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
        'verify_email': EmailVerificationSerializer,
        'resend_verification': ResendVerificationSerializer,
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
        Public: register, login, verify_email, resend_verification,
                password_reset, password_reset_confirm
        Protected: logout, password_change, me
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
        Create a new user account with email verification required.

        **Registration Flow:**
        1. Submit registration details
        2. Account created with is_active=False
        3. Verification email sent
        4. User must verify email to activate account
        """,
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                response=RegistrationResponseSerializer,
                description='User account created, verification email sent',
            ),
            400: OpenApiResponse(description='Validation errors'),
        },
        tags=['Authentication'],
    )
    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register new user (student or instructor)

        Creates account with is_active=False and sends verification email.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # User is created with verification token already generated
        user = serializer.save()

        # Send verification email asynchronously
        send_verification_email.delay(user_id=str(user.id), token=user.email_verification_token)

        response_serializer = RegistrationResponseSerializer(
            {
                'message': SuccessMessage.REGISTRATION_SUCCESS,
                'user': user,
            }
        )

        return self.created(response_serializer.data)

    # ═══════════════════════════════════════════════════════════
    # EMAIL VERIFICATION
    # ═══════════════════════════════════════════════════════════

    @extend_schema(
        summary='Verify email address',
        description="""
        Verify user email using token from verification email.

        **Verification Flow:**
        1. User clicks link in verification email
        2. Submit user_id and token
        3. Account activated (is_active=True)
        4. Welcome email sent
        5. Auto-enrolled in intro courses
        """,
        request=EmailVerificationSerializer,
        responses={
            200: OpenApiResponse(
                description='Email verified successfully',
                examples=[
                    OpenApiExample(
                        name='Success',
                        value={'message': 'Email verified successfully. You can now login.'},
                    )
                ],
            ),
            400: OpenApiResponse(description='Invalid or expired token'),
        },
        tags=['Authentication'],
    )
    @action(detail=False, methods=['post'], url_path='verify-email')
    def verify_email(self, request):
        """Verify user email with token"""
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Verify email (activates account and clears token)
        # This will trigger post_save signal which sends welcome email
        # and auto-enrolls students in intro courses
        user.verify_email()

        return self.ok({'message': SuccessMessage.EMAIL_VERIFIED_SUCCESS})

    # ═══════════════════════════════════════════════════════════
    # RESEND VERIFICATION
    # ═══════════════════════════════════════════════════════════

    @extend_schema(
        summary='Resend verification email',
        description="""
        Request a new verification email.

        **Security:** Returns success even if email doesn't exist
        to prevent email enumeration.
        """,
        request=ResendVerificationSerializer,
        responses={
            200: OpenApiResponse(
                description='Verification email sent (if account exists)',
            ),
        },
        tags=['Authentication'],
    )
    @action(detail=False, methods=['post'], url_path='resend-verification')
    def resend_verification(self, request):
        """Resend verification email"""
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)

            # Only send if not already verified
            if not user.is_active:
                # Generate new token (automatically clears old one)
                user.generate_verification_token()

                # Send email
                send_verification_email.delay(
                    user_id=str(user.id), token=user.email_verification_token
                )

        except User.DoesNotExist:
            pass  # Prevent email enumeration

        return self.ok({'message': SuccessMessage.RESEND_VERIFICATION_MESSAGE})

    # ═══════════════════════════════════════════════════════════
    # USER LOGIN
    # ═══════════════════════════════════════════════════════════

    @extend_schema(
        summary='Login to your account',
        description="""
        Authenticate with email and password to receive JWT tokens.

        **Note:** Account must be verified (email confirmed) to login.
        """,
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(
                response=LoginResponseSerializer,
                description='Login successful',
            ),
            400: OpenApiResponse(description='Invalid credentials'),
            401: OpenApiResponse(description='Account inactive'),
        },
        tags=['Authentication'],
    )
    @action(detail=False, methods=['post'])
    def login(self, request):
        """Login with email and password"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Serialize user data
        user_data = UserProfileSerializer(user).data

        response_data = {
            'message': SuccessMessage.LOGIN_SUCCESS,
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': user_data,
        }

        # Validate output
        response_serializer = LoginResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)

        return self.ok(response_serializer.data)

    # ═══════════════════════════════════════════════════════════
    # USER LOGOUT
    # ═══════════════════════════════════════════════════════════

    @extend_schema(
        summary='Logout from your account',
        description="""
        Invalidate the refresh token to logout.
        """,
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'refresh': {
                        'type': 'string',
                        'description': 'The refresh token to blacklist',
                    }
                },
                'required': ['refresh'],
            }
        },
        responses={
            200: OpenApiResponse(description='Logout successful'),
            400: OpenApiResponse(description='Invalid token'),
        },
        tags=['Authentication'],
    )
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Logout current user"""
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
            # Token blacklist app not installed
            response_serializer = LogoutWithWarningResponseSerializer(
                {
                    'message': SuccessMessage.LOGOUT_SUCCESS,
                    'warning': (
                        'Token blacklist not enabled. '
                        'Add rest_framework_simplejwt.token_blacklist to INSTALLED_APPS.'
                    ),
                }
            )
            return self.ok(response_serializer.data)

        except TokenError:
            return self.bad_request(
                message=ErrorMessage.LOGOUT_FAILED,
                code={'refresh': ['Token is invalid or expired']},
            )

        response_serializer = LogoutSuccessResponseSerializer(
            {
                'message': SuccessMessage.LOGOUT_SUCCESS,
            }
        )
        return self.ok(response_serializer.data)

    # ═══════════════════════════════════════════════════════════
    # PASSWORD RESET REQUEST
    # ═══════════════════════════════════════════════════════════

    @extend_schema(
        summary='Request a password reset link',
        description="""
        Send a password reset link to the user's email address.
        """,
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(description='Reset email sent'),
        },
        tags=['Authentication'],
    )
    @action(detail=False, methods=['post'], url_path='password-reset')
    def password_reset(self, request):
        """Request password reset"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        debug_payload = None

        try:
            user = User.objects.get(email=email, is_active=True)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = (
                f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}"
                f"/reset-password/{uid}/{token}/"
            )

            # Send email asynchronously via Celery
            if not getattr(settings, 'PASSWORD_RESET_DISABLE_EMAIL', False):
                send_password_reset_email.delay(user_id=str(user.id), reset_url=reset_link)

            # Debug info (dev only)
            if getattr(settings, 'PASSWORD_RESET_DEBUG_EXPOSE_TOKENS', settings.DEBUG):
                debug_payload = {
                    'uid': uid,
                    'token': token,
                    'reset_link': reset_link,
                }

        except User.DoesNotExist:
            pass  # Prevent email enumeration

        response_serializer = PasswordResetResponseSerializer(
            {
                'message': SuccessMessage.PASSWORD_RESET_EMAIL_SENT,
                **({'debug': debug_payload} if debug_payload else {}),
            }
        )

        return self.ok(response_serializer.data)

    # ═══════════════════════════════════════════════════════════
    # PASSWORD RESET CONFIRMATION
    # ═══════════════════════════════════════════════════════════

    @extend_schema(
        summary='Complete password reset with token',
        description="""
        Reset password using the token received via email.
        """,
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(description='Password reset successful'),
            400: OpenApiResponse(description='Invalid token'),
        },
        tags=['Authentication'],
    )
    @action(detail=False, methods=['post'], url_path='password-reset-confirm')
    def password_reset_confirm(self, request):
        """Confirm password reset"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        new_password = serializer.validated_data['new_password']

        # Set new password
        user.set_password(new_password)
        user.save(update_fields=['password'])

        # Send confirmation email asynchronously via Celery
        send_password_reset_confirmation_email.delay(user_id=str(user.id))

        response_serializer = MessageOnlyResponseSerializer(
            {
                'message': SuccessMessage.PASSWORD_RESET_SUCCESS,
            }
        )

        return self.ok(response_serializer.data)

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

        # ---------- GET ----------
        if request.method == 'GET':
            response_serializer = MeResponseSerializer({'user': self.get_serializer(user).data})
            return self.ok(response_serializer.data)

        # ---------- PUT / PATCH ----------
        serializer = self.get_serializer(
            user,
            data=request.data,
            partial=(request.method == 'PATCH'),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_serializer = MeResponseSerializer({'user': serializer.data})
        return self.ok(response_serializer.data)


__all__ = ['AuthViewSet']
