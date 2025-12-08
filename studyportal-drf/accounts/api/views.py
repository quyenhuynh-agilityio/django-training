from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

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
    TokenResponseSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
)

User = get_user_model()


class UserRegistrationView(CommonViewSet, generics.CreateAPIView):
    """
    Student Registration API

    POST /api/v1/auth/register/

    Register a new student account.
    - Email must be unique
    - Password must meet security requirements
    - Automatically assigns 'student' role

    Returns:
    - 201: User created successfully
    - 400: Validation errors
    """

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

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
        """Handle POST request for registration"""
        serializer = self.get_serializer(data=request.data)

        try:
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

        except serializers.ValidationError as e:
            return self.bad_request(
                message='Registration failed. Please check your input.', code=e.detail
            )

        except Exception as e:
            return Response(
                {'message': 'An unexpected error occurred during registration.', 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserLoginView(CommonViewSet, APIView):
    """
    User Login API

    POST /api/v1/auth/login/

    Authenticate user and return JWT tokens.
    - Validates email and password
    - Returns access and refresh tokens
    - Works for all user roles (student, instructor, admin)

    Returns:
    - 200: Login successful with tokens
    - 400: Invalid credentials
    - 401: User account disabled
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary='User login',
        description='Authenticate user with email and password, returns JWT tokens',
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(
                response=TokenResponseSerializer,
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
        """Handle POST request for login"""
        serializer = UserLoginSerializer(data=request.data)

        try:
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

        except serializers.ValidationError as e:
            return self.bad_request(message='Login failed', code=e.detail)

        except Exception as e:
            return Response(
                {'message': 'An unexpected error occurred during login.', 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PasswordResetRequestView(CommonViewSet, APIView):
    """
    Password Reset Request API

    POST /api/v1/auth/password/reset/

    Request password reset by email.
    - Sends reset link to user's email
    - Token valid for 24 hours
    - Doesn't reveal if email exists (security)

    Returns:
    - 200: Reset email sent (always, even if email doesn't exist)
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary='Request password reset',
        description="Send password reset link to user's email",
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                description='Reset email sent',
                examples=[
                    OpenApiExample(
                        'Success',
                        value={
                            'message': 'If an account exists with this email, a password reset link has been sent.'
                        },
                    )
                ],
            )
        },
        tags=['Authentication'],
    )
    def post(self, request):
        """Handle POST request for password reset"""
        serializer = PasswordResetRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return self.bad_request(message='Invalid email format', code=serializer.errors)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_active=True)

            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Create reset link
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            reset_link = f'{frontend_url}/reset-password/{uid}/{token}/'

            # Send email
            try:
                send_mail(
                    subject='Password Reset Request',
                    message=f'Click the link below to reset your password:\n\n{reset_link}\n\nThis link will expire in 24 hours.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as email_error:
                # Log error but don't reveal to user
                print(f'Email error: {email_error}')

        except User.DoesNotExist:
            # Don't reveal if email doesn't exist
            pass

        # Always return success (security measure)
        return self.ok(
            {
                'message': 'If an account exists with this email, a password reset link has been sent.'
            }
        )


class PasswordResetConfirmView(CommonViewSet, APIView):
    """
    Password Reset Confirmation API

    POST /api/v1/auth/password/reset/confirm/

    Confirm password reset with token.
    - Validates reset token
    - Sets new password
    - Token can only be used once

    Returns:
    - 200: Password reset successful
    - 400: Invalid token or validation errors
    """

    permission_classes = [permissions.AllowAny]

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
        """Handle POST request for password reset confirmation"""
        serializer = PasswordResetConfirmSerializer(data=request.data)

        try:
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

        except serializers.ValidationError as e:
            return self.bad_request(message='Password reset failed', code=e.detail)

        except Exception as e:
            return Response(
                {'message': 'An unexpected error occurred during password reset.', 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ChangePasswordView(CommonViewSet, APIView):
    """
    Change Password API (Authenticated)

    POST /api/v1/auth/password/change/

    Change password for authenticated user.
    - Requires authentication
    - Validates old password
    - Sets new password

    Returns:
    - 200: Password changed successfully
    - 400: Validation errors
    - 401: Unauthorized
    """

    permission_classes = [permissions.IsAuthenticated]

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
        """Handle POST request for password change"""
        serializer = ChangePasswordSerializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)

            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']

            # Check old password
            if not user.check_password(old_password):
                return self.bad_request(
                    message='Password change failed', code={'old_password': ['Wrong password.']}
                )

            # Set new password
            user.set_password(new_password)
            user.save()

            return self.ok({'message': 'Password changed successfully'})

        except serializers.ValidationError as e:
            return self.bad_request(message='Password change failed', code=e.detail)


class UserLogoutView(CommonViewSet, APIView):
    """
    User Logout API (Optional - Token Blacklisting)

    POST /api/v1/auth/logout/

    Logout user by blacklisting refresh token.
    - Requires authentication
    - Invalidates refresh token
    - Access token remains valid until expiration

    Returns:
    - 200: Logout successful
    - 400: Invalid token
    """

    permission_classes = [permissions.IsAuthenticated]

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
        """Handle POST request for logout"""
        try:
            refresh_token = request.data.get('refresh')

            if not refresh_token:
                return self.bad_request(
                    message='Logout failed', code={'error': 'Refresh token is required'}
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            return self.ok({'message': 'Logout successful'})

        except TokenError:
            return self.bad_request(
                message='Logout failed', code={'error': 'Token is invalid or expired'}
            )

        except Exception as e:
            return self.bad_request(message='Logout failed', code={'error': str(e)})


class UserProfileView(CommonViewSet, generics.RetrieveUpdateAPIView):
    """
    User Profile API

    GET /api/v1/auth/me/
    PUT /api/v1/auth/me/

    Get or update user profile.
    - Requires authentication
    - Can update first_name, last_name
    - Cannot change email, username, role

    Returns:
    - 200: Profile data
    - 401: Unauthorized
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    @extend_schema(
        summary='Get user profile',
        description="Get authenticated user's profile",
        responses={200: UserProfileSerializer},
        tags=['Authentication'],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary='Update user profile',
        description="Update authenticated user's profile (first_name, last_name)",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
        tags=['Authentication'],
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary='Partial update user profile',
        description="Partially update authenticated user's profile",
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
        tags=['Authentication'],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
