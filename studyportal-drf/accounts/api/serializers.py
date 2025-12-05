from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Student Registration Serializer

    Validation:
    - Email must be unique and valid format
    - Password must meet Django's password validation
    - Password confirmation must match
    - All required fields must be present
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text='Password must be at least 8 characters',
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Re-enter password for confirmation',
    )

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
            'password_confirm',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'email': {'required': True, 'help_text': 'Valid email address'},
            'username': {'required': True, 'help_text': 'Unique username (alphanumeric)'},
            'first_name': {'required': True, 'help_text': 'First name'},
            'last_name': {'required': True, 'help_text': 'Last name'},
        }

    def validate_email(self, value):
        """
        Field-level validation for email
        - Convert to lowercase
        - Check uniqueness
        """
        value = value.lower().strip()

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email address already exists.')

        return value

    def validate_username(self, value):
        """
        Field-level validation for username
        - Must be alphanumeric
        - Check uniqueness
        """
        value = value.strip()

        if not value.replace('_', '').isalnum():
            raise serializers.ValidationError(
                'Username must contain only letters, numbers, and underscores.'
            )

        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')

        return value

    def validate_first_name(self, value):
        """Validate first name is not empty"""
        value = value.strip()
        if not value:
            raise serializers.ValidationError('First name cannot be empty.')
        return value

    def validate_last_name(self, value):
        """Validate last name is not empty"""
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Last name cannot be empty.')
        return value

    def validate(self, attrs):
        """
        Object-level validation
        - Check password confirmation matches
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password': "Password fields didn't match."})

        return attrs

    def create(self, validated_data):
        """
        Create user with hashed password
        - Remove password_confirm
        - Set role to 'student'
        - Use create_user for proper password hashing
        """
        validated_data.pop('password_confirm')

        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password'],
            role='student',  # Force student role for registration
        )

        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Login Serializer

    Validation:
    - Email and password required
    - Credentials must be valid
    - User must be active
    """

    email = serializers.EmailField(required=True, help_text='Email address')
    password = serializers.CharField(
        write_only=True, required=True, style={'input_type': 'password'}, help_text='Password'
    )

    def validate_email(self, value):
        """Normalize email to lowercase"""
        return value.lower().strip()

    def validate(self, attrs):
        """
        Object-level validation
        - Check credentials
        - Check user is active
        """
        email = attrs.get('email')
        password = attrs.get('password')

        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({'detail': 'Invalid email or password.'})  # noqa: B904

        # Check if user is active
        if not user.is_active:
            raise serializers.ValidationError({'detail': 'User account is disabled.'})

        # Check password
        if not user.check_password(password):
            raise serializers.ValidationError({'detail': 'Invalid email or password.'})

        attrs['user'] = user
        return attrs


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token response"""

    access_token = serializers.CharField(help_text='Access token')
    refresh_token = serializers.CharField(help_text='Refresh token')
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        """Return user info"""
        user = obj.get('user')
        return {
            'id': str(user.id),
            'email': user.email,
            'username': user.username,
            'full_name': user.full_name,
            'role': user.role,
        }


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Password Reset Request Serializer

    Validation:
    - Email must be valid format
    - Don't reveal if email exists (security)
    """

    email = serializers.EmailField(required=True, help_text='Email address associated with account')

    def validate_email(self, value):
        """Normalize email"""
        return value.lower().strip()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Password Reset Confirmation Serializer

    Validation:
    - UID and token must be valid
    - New password must meet requirements
    - Password confirmation must match
    """

    uid = serializers.CharField(required=True, help_text='User ID (base64 encoded)')
    token = serializers.CharField(required=True, help_text='Password reset token')
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text='New password',
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Confirm new password',
    )

    def validate(self, attrs):
        """
        Object-level validation
        - Check passwords match
        - Validate token
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password': "Password fields didn't match."})

        # Validate UID and token
        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({'detail': 'Invalid reset link.'})  # noqa: B904

        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({'detail': 'Invalid or expired reset token.'})

        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """
    Change Password Serializer (for authenticated users)

    Validation:
    - Old password must be correct
    - New password must meet requirements
    - New password must be different from old
    """

    old_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Current password',
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text='New password',
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Confirm new password',
    )

    def validate(self, attrs):
        """
        Object-level validation
        - Check passwords match
        - Check new password different from old
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password': "Password fields didn't match."})

        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {'new_password': 'New password must be different from old password.'}
            )

        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """User Profile Serializer"""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'is_active',
            'date_joined',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'email',
            'username',
            'role',
            'is_active',
            'date_joined',
            'created_at',
        ]
