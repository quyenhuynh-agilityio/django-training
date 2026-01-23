from datetime import timedelta
from uuid import uuid4

import pytest

from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import serializers

from users.api.serializers import (
    ChangePasswordSerializer,
    EmailVerificationSerializer,
    PasswordResetConfirmSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
)

pytestmark = pytest.mark.django_db


def test_registration_serializer_creates_student_user():
    data = {
        'email': 'newuser@example.com',
        'username': 'newuser',
        'first_name': 'New',
        'last_name': 'User',
        'password': 'StrongPass123',
        'password_confirm': 'StrongPass123',
    }

    serializer = UserRegistrationSerializer(data=data)
    assert serializer.is_valid(), serializer.errors

    user = serializer.save()

    assert user.role == 'student'
    assert user.email == 'newuser@example.com'
    assert user.check_password('StrongPass123') is True


def test_registration_serializer_rejects_duplicate_email(create_user):
    create_user(email='dupe@example.com', username='existing')

    data = {
        'email': 'dupe@example.com',
        'username': 'newuser',
        'first_name': 'New',
        'last_name': 'User',
        'password': 'StrongPass123',
        'password_confirm': 'StrongPass123',
    }

    serializer = UserRegistrationSerializer(data=data)
    assert serializer.is_valid() is False
    assert 'email' in serializer.errors


def test_registration_serializer_rejects_bad_username():
    serializer = UserRegistrationSerializer(
        data={
            'email': 'newbad@example.com',
            'username': 'bad username!',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'StrongPass123',
            'password_confirm': 'StrongPass123',
        }
    )

    assert serializer.is_valid() is False
    assert 'username' in serializer.errors


def test_registration_serializer_requires_matching_passwords():
    serializer = UserRegistrationSerializer(
        data={
            'email': 'mismatch@example.com',
            'username': 'mismatchuser',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'StrongPass123',
            'password_confirm': 'OtherPass123',
        }
    )

    assert serializer.is_valid() is False
    assert 'password_confirm' in serializer.errors


def test_login_serializer_validates_credentials(create_user):
    user = create_user(email='login@example.com', username='loginuser', password='StrongPass123')

    serializer = UserLoginSerializer(
        data={'email': 'login@example.com', 'password': 'StrongPass123'}
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['user'] == user


def test_login_serializer_rejects_inactive_user(create_user):
    create_user(
        email='inactive@example.com',
        username='inactive',
        password='StrongPass123',
        is_active=False,
    )

    serializer = UserLoginSerializer(
        data={'email': 'inactive@example.com', 'password': 'StrongPass123'}
    )
    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_login_serializer_rejects_invalid_credentials():
    serializer = UserLoginSerializer(
        data={'email': 'missing@example.com', 'password': 'WrongPass123'}
    )

    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_password_reset_confirm_serializer_accepts_valid_token(create_user):
    user = create_user(email='reset@example.com', username='resetuser')

    from django.contrib.auth.tokens import default_token_generator

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    serializer = PasswordResetConfirmSerializer(
        data={
            'uid': uid,
            'token': token,
            'new_password': 'NewStrongPass123',
            'new_password_confirm': 'NewStrongPass123',
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['user'] == user


def test_change_password_serializer_rejects_same_password(api_client, create_user):
    user = create_user(email='changepw@example.com', username='changepw', password='SamePass123')
    api_client.force_authenticate(user=user)

    # Create a mock request object with user
    from rest_framework.test import APIRequestFactory

    factory = APIRequestFactory()
    request = factory.post('/')
    request.user = user

    serializer = ChangePasswordSerializer(
        data={
            'old_password': 'SamePass123',
            'new_password': 'SamePass123',
            'new_password_confirm': 'SamePass123',
        },
        context={'request': request},
    )

    assert serializer.is_valid() is False
    assert 'new_password' in serializer.errors


def test_email_verification_serializer_valid_token(create_user):
    """Test email verification with valid token"""

    user = create_user(email='verify@example.com', username='verify', is_active=False)
    token = user.generate_verification_token()

    serializer = EmailVerificationSerializer(data={'user_id': str(user.id), 'token': token})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['user'] == user


def test_email_verification_serializer_invalid_user_id():
    """Test email verification with invalid user ID"""
    serializer = EmailVerificationSerializer(data={'user_id': 'invalid-uuid', 'token': 'sometoken'})
    assert serializer.is_valid() is False
    assert 'user_id' in serializer.errors


def test_email_verification_serializer_nonexistent_user():
    """Test email verification with nonexistent user"""
    serializer = EmailVerificationSerializer(
        data={'user_id': str(uuid4()), 'token': 'sometokenlongenoughtomeetminimumlength'}
    )
    assert serializer.is_valid() is False
    assert 'detail' in serializer.errors


def test_email_verification_serializer_already_active_user(create_user):
    """Test email verification for already active user"""
    user = create_user(email='active@example.com', username='active', is_active=True)
    token = user.generate_verification_token()

    serializer = EmailVerificationSerializer(data={'user_id': str(user.id), 'token': token})
    assert serializer.is_valid() is False
    assert 'detail' in serializer.errors


def test_email_verification_serializer_invalid_token(create_user):
    """Test email verification with invalid token"""

    user = create_user(email='invalid@example.com', username='invalid', is_active=False)

    serializer = EmailVerificationSerializer(
        data={'user_id': str(user.id), 'token': 'invalidtokenlongenoughtomeetminimumlength'}
    )
    assert serializer.is_valid() is False
    assert 'detail' in serializer.errors


def test_email_verification_serializer_expired_token(create_user, settings):
    """Test email verification with expired token"""

    # Set expiry to 1 hour for test
    settings.EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 1

    user = create_user(email='expired@example.com', username='expired', is_active=False)
    token = user.generate_verification_token()

    # Make token old
    user.email_verification_token_created = timezone.now() - timedelta(hours=2)
    user.save()

    serializer = EmailVerificationSerializer(data={'user_id': str(user.id), 'token': token})
    assert serializer.is_valid() is False
    assert 'detail' in serializer.errors
