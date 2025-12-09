import pytest

from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import serializers

from accounts.api.serializers import (
    ChangePasswordSerializer,
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
    assert 'password' in serializer.errors


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


def test_change_password_serializer_rejects_same_password():
    serializer = ChangePasswordSerializer(
        data={
            'old_password': 'SamePass123',
            'new_password': 'SamePass123',
            'new_password_confirm': 'SamePass123',
        }
    )

    assert serializer.is_valid() is False
    assert 'new_password' in serializer.errors
