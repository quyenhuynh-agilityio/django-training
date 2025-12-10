"""
Authentication API Views

This module contains all authentication-related API endpoints:
- User registration (students)
- Login/Logout (JWT tokens)
- Password management (change, reset)
- User profile management

All views inherit from CommonViewSet for consistent response formatting.
"""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api_views import CommonViewSet

from .serializers import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)

# Get the custom User model
User = get_user_model()


# ============================================
# USER REGISTRATION
# ============================================


class UserRegistrationView(CommonViewSet, generics.CreateAPIView):
    """
    Student Registration API

    Endpoint: POST /api/v1/auth/register/
    Permission: AllowAny (public access)

    Features:
    - Registers new student accounts
    - Email must be unique
    - Password validation (min 8 chars, not too common)
    - Automatically assigns 'student' role
    - Returns user data (without password)

    Request Body:
        {
            "email": "student@example.com",
            "username": "student123",
            "first_name": "John",
            "last_name": "Doe",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!"
        }

    Response (201 Created):
        {
            "message": "Registration successful. Please login.",
            "user": {
                "id": "uuid",
                "email": "student@example.com",
                "username": "student123",
                "first_name": "John",
                "last_name": "Doe",
                "role": "student"
            }
        }

    Error Response (400 Bad Request):
        {
            "message": "Registration failed. Please check your input.",
            "errors": {
                "email": ["A user with this email address already exists."]
            }
        }
    """

    # Queryset and serializer configuration
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]  # Public endpoint

    @extend_schema(
        summary='Register new student',
        description='Create a new student account with email and password',
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(
                response=UserRegistrationSerializer,
                description='User registered successfully',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'id': '123e4567-e89b-12d3-a456-426614174000',
                            'email': 'student@example.com',
                            'username': 'student123',
                            'first_name': 'John',
                            'last_name': 'Doe',
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
                    OpenApiExample(
                        'Password mismatch', value={'password': ["Password fields didn't match."]}
                    ),
                ],
            ),
        },
        tags=['Authentication'],
    )
    def post(self, request, *args, **kwargs):
        """
        Handle POST request for user registration

        Process:
        1. Validate input data using serializer
        2. Create new user with hashed password
        3. Return user data (without password)

        Args:
            request: HTTP request with registration data

        Returns:
            Response with user data or validation errors
        """
        # Initialize serializer with request data
        serializer = self.get_serializer(data=request.data)

        try:
            # Validate data (raises ValidationError if invalid)
            serializer.is_valid(raise_exception=True)

            # Create user (password is hashed in serializer)
            user = serializer.save()

            # Return success response using CommonViewSet method
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

        except serializers.ValidationError as e:
            # Handle validation errors (e.g., duplicate email, password mismatch)
            return self.bad_request(
                message='Registration failed. Please check your input.', code=e.detail
            )

        except Exception as e:
            # Handle unexpected errors (should be logged in production)
            return Response(
                {'message': 'An unexpected error occurred during registration.', 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================
# USER LOGIN
# ============================================


class UserLoginView(CommonViewSet, APIView):
    """
    User Login API

    Endpoint: POST /api/v1/auth/login/
    Permission: AllowAny (public access)

    Features:
    - Authenticates users with email and password
    - Generates JWT access and refresh tokens
    - Works for all roles (student, instructor, admin)
    - Returns user information and tokens

    Request Body:
        {
            "email": "student@example.com",
            "password": "SecurePass123!"
        }

    Response (200 OK):
        {
            "message": "Login successful",
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "user": {
                "id": "uuid",
                "email": "student@example.com",
                "username": "student123",
                "full_name": "John Doe",
                "role": "student"
            }
        }

    Error Response (400 Bad Request):
        {
            "message": "Login failed",
            "errors": {
                "detail": "Invalid email or password."
            }
        }

    JWT Token Details:
    - Access token: Valid for 24 hours (configurable)
    - Refresh token: Valid for 7 days (configurable)
    - Use access token in Authorization header: Bearer <token>
    - Use refresh token to get new access token
    """

    permission_classes = [permissions.AllowAny]  # Public endpoint

    @extend_schema(
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
    )
    def post(self, request):
        """
        Handle POST request for user login

        Process:
        1. Validate email and password
        2. Check user exists and is active
        3. Generate JWT tokens
        4. Return tokens and user info

        Args:
            request: HTTP request with login credentials

        Returns:
            Response with JWT tokens and user data or error
        """
        # Initialize serializer with request data
        serializer = UserLoginSerializer(data=request.data)

        try:
            # Validate credentials (serializer checks email/password)
            serializer.is_valid(raise_exception=True)

            # Get validated user from serializer
            user = serializer.validated_data['user']

            # Generate JWT tokens for the user
            refresh = RefreshToken.for_user(user)

            # Return success response with tokens and user info
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

        except serializers.ValidationError as e:
            # Handle validation errors (invalid credentials, inactive account)
            return self.bad_request(message='Login failed', code=e.detail)

        except Exception as e:
            # Handle unexpected errors
            return Response(
                {'message': 'An unexpected error occurred during login.', 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================
# PASSWORD RESET REQUEST
# ============================================


class PasswordResetRequestView(CommonViewSet, APIView):
    """
    Password Reset Request API

    Endpoint: POST /api/v1/auth/password/reset/
    Permission: AllowAny (public access)

    Features:
    - Sends password reset link to user's email
    - Token valid for 24 hours
    - Security: Doesn't reveal if email exists
    - Same response whether email exists or not

    Request Body:
        {
            "email": "student@example.com"
        }

    Response (200 OK) - Always:
        {
            "message": "If an account exists with this email, a password reset link has been sent."
        }

    Email Content:
    - Subject: "Password Reset Request"
    - Contains unique reset link with token
    - Link format: {FRONTEND_URL}/reset-password/{uid}/{token}/
    - Token expires after 24 hours

    Security Note:
    - Always returns same message (doesn't reveal email existence)
    - Token is single-use only
    - Old tokens invalidated when new password set
    """

    permission_classes = [permissions.AllowAny]  # Public endpoint

    @extend_schema(
        summary='Request password reset',
        description=(
            'Generate a password reset token. In DEBUG or when '
            '`PASSWORD_RESET_DEBUG_EXPOSE_TOKENS` is True, the response also '
            'includes the `uid`, `token`, and `reset_link` so you can test the '
            'confirm step directly in Swagger without receiving an email.'
        ),
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                description='Reset email sent or token generated',
                examples=[
                    OpenApiExample(
                        'Success (debug payload included)',
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
    )
    def post(self, request):
        """
        Handle POST request for password reset

        Process:
        1. Validate email format
        2. Check if user exists (internal only)
        3. Generate reset token and link
        4. Send email with reset link
        5. Return generic success message (security)

        Args:
            request: HTTP request with email

        Returns:
            Response with generic success message

        Security:
            Always returns success to prevent email enumeration
        """
        # Initialize serializer with request data
        serializer = PasswordResetRequestSerializer(data=request.data)

        # Validate email format
        if not serializer.is_valid():
            return self.bad_request(message='Invalid email format', code=serializer.errors)

        # Get validated email
        email = serializer.validated_data['email']

        try:
            # Try to find active user with this email
            user = User.objects.get(email=email, is_active=True)

            # Generate password reset token (Django built-in)
            token = default_token_generator.make_token(user)

            # Encode user ID for URL (base64)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Build reset link for frontend
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_link = f'{frontend_url}/reset-password/{uid}/{token}/'

            # Optional debug payload to make testing easier (e.g., via Swagger)
            debug_expose = getattr(settings, 'PASSWORD_RESET_DEBUG_EXPOSE_TOKENS', settings.DEBUG)
            debug_payload = (
                {'uid': uid, 'token': token, 'reset_link': reset_link} if debug_expose else None
            )

            # Optionally skip sending emails when testing locally
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
                    # Log error but don't reveal to user (security)
                    # In production, use proper logging
                    print(f'Email error: {email_error}')
            else:
                # For local Swagger testing we intentionally skip email sending
                print('Password reset email skipped (PASSWORD_RESET_DISABLE_EMAIL=True)')
        except User.DoesNotExist:
            # User doesn't exist - don't reveal this (security measure)
            # Continue to return success message
            debug_payload = None

        # Always return success message (security: don't reveal if email exists)
        response_payload = {
            'message': 'If an account exists with this email, a password reset link has been sent.'
        }

        # Include tokens in response only in explicitly allowed environments
        if debug_payload:
            response_payload['debug'] = debug_payload

        return self.ok(response_payload)


# ============================================
# PASSWORD RESET CONFIRMATION
# ============================================


class PasswordResetConfirmView(CommonViewSet, APIView):
    """
    Password Reset Confirmation API

    Endpoint: POST /api/v1/auth/password/reset/confirm/
    Permission: AllowAny (public access)

    Features:
    - Validates reset token from email
    - Sets new password
    - Token is single-use only
    - Token expires after 24 hours

    Request Body:
        {
            "uid": "MQ",  # Base64 encoded user ID
            "token": "abc123...",  # Reset token from email
            "new_password": "NewSecurePass123!",
            "new_password_confirm": "NewSecurePass123!"
        }

    Response (200 OK):
        {
            "message": "Password has been reset successfully. You can now login with your new password."
        }

    Error Response (400 Bad Request):
        {
            "message": "Password reset failed",
            "errors": {
                "detail": "Invalid or expired reset token."
            }
        }

    Process Flow:
    1. User requests reset (gets email with uid/token)
    2. User clicks link, frontend extracts uid/token
    3. Frontend sends uid/token/new_password to this endpoint
    4. Backend validates token and updates password
    5. User can login with new password
    """

    permission_classes = [permissions.AllowAny]  # Public endpoint

    @extend_schema(
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
    )
    def post(self, request):
        """
        Handle POST request for password reset confirmation

        Process:
        1. Validate uid, token, and new password
        2. Decode uid to get user
        3. Verify token is valid for this user
        4. Set new password (hashed)
        5. Invalidate token

        Args:
            request: HTTP request with uid, token, and new password

        Returns:
            Response with success message or error

        Note:
            Token is automatically invalidated after password change
        """
        # Initialize serializer with request data
        serializer = PasswordResetConfirmSerializer(data=request.data)

        try:
            # Validate token and passwords
            # Serializer handles:
            # - Decoding uid
            # - Validating token
            # - Checking password match
            # - Password strength validation
            serializer.is_valid(raise_exception=True)

            # Get validated user and new password
            user = serializer.validated_data['user']
            new_password = serializer.validated_data['new_password']

            # Set new password (Django hashes it automatically)
            user.set_password(new_password)
            user.save()

            # Token is now invalidated (can't be reused)

            # Return success message
            return self.ok(
                {
                    'message': 'Password has been reset successfully. You can now login with your new password.'
                }
            )

        except serializers.ValidationError as e:
            # Handle validation errors (invalid token, password mismatch)
            return self.bad_request(message='Password reset failed', code=e.detail)

        except Exception as e:
            # Handle unexpected errors
            return Response(
                {'message': 'An unexpected error occurred during password reset.', 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================
# CHANGE PASSWORD (AUTHENTICATED)
# ============================================


class ChangePasswordView(CommonViewSet, APIView):
    """
    Change Password API (Authenticated Users)

    Endpoint: POST /api/v1/auth/password/change/
    Permission: IsAuthenticated (requires login)

    Features:
    - Allows logged-in users to change their password
    - Validates old password before changing
    - Requires authentication (JWT token)

    Request Body:
        {
            "old_password": "CurrentPass123!",
            "new_password": "NewSecurePass123!",
            "new_password_confirm": "NewSecurePass123!"
        }

    Request Headers:
        Authorization: Bearer <access_token>

    Response (200 OK):
        {
            "message": "Password changed successfully"
        }

    Error Response (400 Bad Request):
        {
            "message": "Password change failed",
            "errors": {
                "old_password": ["Wrong password."]
            }
        }

    Use Cases:
    - User wants to update password while logged in
    - Security: Change password after suspicious activity
    - Compliance: Regular password updates

    Difference from Reset:
    - Requires authentication (vs anonymous reset)
    - Needs old password (vs token from email)
    - Immediate (vs email-based flow)
    """

    permission_classes = [permissions.IsAuthenticated]  # Requires login

    @extend_schema(
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
    )
    def post(self, request):
        """
        Handle POST request for password change

        Process:
        1. Verify user is authenticated
        2. Validate old password
        3. Validate new password (strength, match)
        4. Update password

        Args:
            request: HTTP request with password data

        Returns:
            Response with success message or error

        Security:
            Requires valid JWT token in Authorization header
        """
        # Initialize serializer with request data
        serializer = ChangePasswordSerializer(data=request.data)

        try:
            # Validate passwords
            # Serializer checks:
            # - New passwords match
            # - New password different from old
            # - Password strength
            serializer.is_valid(raise_exception=True)

            # Get current user from request (authenticated)
            user = request.user

            # Get validated password data
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']

            # Verify old password is correct
            if not user.check_password(old_password):
                return self.bad_request(
                    message='Password change failed', code={'old_password': ['Wrong password.']}
                )

            # Set new password (Django hashes it)
            user.set_password(new_password)
            user.save()

            # Note: User remains logged in (JWT token still valid)
            # Frontend may want to re-login for new token

            return self.ok({'message': 'Password changed successfully'})

        except serializers.ValidationError as e:
            # Handle validation errors
            return self.bad_request(message='Password change failed', code=e.detail)


# ============================================
# USER LOGOUT
# ============================================


class UserLogoutView(CommonViewSet, APIView):
    """
    User Logout API (Token Blacklisting)

    Endpoint: POST /api/v1/auth/logout/
    Permission: IsAuthenticated (requires login)

    Features:
    - Blacklists refresh token to prevent reuse
    - Access token remains valid until expiration
    - Requires authentication

    Request Body:
        {
            "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."  # Refresh token
        }

    Request Headers:
        Authorization: Bearer <access_token>

    Response (200 OK):
        {
            "message": "Logout successful"
        }

    Error Response (400 Bad Request):
        {
            "message": "Logout failed",
            "error": "Token is invalid or expired"
        }

    How JWT Logout Works:
    1. Client sends refresh token to blacklist
    2. Server adds token to blacklist database
    3. Token can no longer be used to get new access tokens
    4. Access token remains valid until natural expiration
    5. Client should delete both tokens locally

    Note:
    - Access tokens are stateless (can't be revoked)
    - They expire after 24 hours (configurable)
    - For immediate revocation, keep token lifetime short
    """

    permission_classes = [permissions.IsAuthenticated]  # Requires login

    @extend_schema(
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
    )
    def post(self, request):
        """
        Handle POST request for logout

        Process:
        1. Verify user is authenticated
        2. Get refresh token from request
        3. Add token to blacklist
        4. Return success

        Args:
            request: HTTP request with refresh token

        Returns:
            Response with success message or error

        Note:
            Client should delete access and refresh tokens locally
        """
        try:
            # Get refresh token from request body
            refresh_token = request.data.get('refresh')

            # Validate refresh token exists
            if not refresh_token:
                return self.bad_request(
                    message='Logout failed', code={'error': 'Refresh token is required'}
                )

            # Create RefreshToken instance
            token = RefreshToken(refresh_token)

            # Add token to blacklist (prevents reuse)
            token.blacklist()

            # Client should now delete both tokens locally
            return self.ok({'message': 'Logout successful'})

        except TokenError:
            # Handle invalid or expired token
            return self.bad_request(
                message='Logout failed', code={'error': 'Token is invalid or expired'}
            )

        except Exception as e:
            # Handle unexpected errors
            return self.bad_request(message='Logout failed', code={'error': str(e)})


# ============================================
# USER PROFILE
# ============================================


class UserProfileView(CommonViewSet, generics.RetrieveUpdateAPIView):
    """
    User Profile API

    Endpoints:
    - GET /api/v1/auth/me/ - Get profile
    - PUT /api/v1/auth/me/ - Full update
    - PATCH /api/v1/auth/me/ - Partial update

    Permission: IsAuthenticated (requires login)

    Features:
    - View current user's profile
    - Update first_name, last_name
    - Read-only: email, username, role

    Request Headers:
        Authorization: Bearer <access_token>

    GET Response (200 OK):
        {
            "id": "uuid",
            "email": "student@example.com",
            "username": "student123",
            "first_name": "John",
            "last_name": "Doe",
            "full_name": "John Doe",
            "role": "student",
            "is_active": true,
            "date_joined": "2024-01-15T10:30:00Z",
            "created_at": "2024-01-15T10:30:00Z"
        }

    PATCH Request Body (partial update):
        {
            "first_name": "Jane",
            "last_name": "Smith"
        }

    PATCH Response (200 OK):
        {
            "id": "uuid",
            "email": "student@example.com",
            "username": "student123",
            "first_name": "Jane",
            "last_name": "Smith",
            "full_name": "Jane Smith",
            "role": "student",
            ...
        }

    Read-Only Fields:
    - id: Cannot be changed
    - email: Cannot be changed (would break authentication)
    - username: Cannot be changed
    - role: Cannot be changed (security)
    - date_joined: System timestamp
    - created_at: System timestamp

    Updatable Fields:
    - first_name: User's first name
    - last_name: User's last name
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]  # Requires login

    def get_object(self):
        """
        Return current authenticated user

        Overrides default get_object to always return request.user
        No need to pass user ID in URL

        Returns:
            User: Currently authenticated user
        """
        return self.request.user

    @extend_schema(
        summary='Get user profile',
        description="Get authenticated user's profile",
        responses={200: UserProfileSerializer},
        tags=['Authentication'],
    )
    def get(self, request, *args, **kwargs):
        """
        Handle GET request for profile

        Returns:
            Response with user profile data
        """
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Update user profile',
        description="Update authenticated user's profile (first_name, last_name)",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
        tags=['Authentication'],
    )
    def put(self, request, *args, **kwargs):
        """
        Handle PUT request for full profile update

        Note: Requires all fields (except read-only)
        Use PATCH for partial updates

        Returns:
            Response with updated user profile
        """
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary='Partial update user profile',
        description="Partially update authenticated user's profile",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
        tags=['Authentication'],
    )
    def patch(self, request, *args, **kwargs):
        """
        Handle PATCH request for partial profile update

        Note: Can update any combination of updatable fields
        More flexible than PUT

        Returns:
            Response with updated user profile
        """
        return super().patch(request, *args, **kwargs)


# ============================================
# TOKEN REFRESH
# ============================================


class TokenRefreshSchemaView(TokenRefreshView):
    """JWT access token refresh endpoint with schema tags."""

    @extend_schema(tags=['Authentication'], summary='Refresh access token')
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
