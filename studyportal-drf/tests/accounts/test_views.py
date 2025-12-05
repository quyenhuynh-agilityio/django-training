import pytest
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status

pytestmark = pytest.mark.django_db


def test_user_registration_view_creates_student(api_client):
    payload = {
        'email': 'student@example.com',
        'username': 'student1',
        'first_name': 'Student',
        'last_name': 'One',
        'password': 'StrongPass123',
        'password_confirm': 'StrongPass123',
    }

    response = api_client.post(reverse('register'), payload, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['message'] == 'Registration successful. Please login.'
    assert response.data['user']['role'] == 'student'

    user = get_user_model().objects.get(email='student@example.com')
    assert user.check_password('StrongPass123') is True


def test_user_login_view_returns_tokens(api_client, create_user):
    user = create_user(email='login@example.com', username='loginuser', password='StrongPass123')

    response = api_client.post(
        reverse('login'),
        {'email': 'login@example.com', 'password': 'StrongPass123'},
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data['user']['id'] == str(user.id)
    assert 'access_token' in response.data
    assert 'refresh_token' in response.data


def test_profile_view_returns_authenticated_user(api_client, create_user):
    user = create_user(email='profile@example.com', username='profileuser')
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse('me'))

    assert response.status_code == status.HTTP_200_OK
    assert response.data['email'] == 'profile@example.com'
    assert response.data['username'] == 'profileuser'


def test_profile_view_updates_name(api_client, create_user):
    user = create_user(email='update@example.com', username='updateuser')
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse('me'),
        {'first_name': 'Updated', 'last_name': 'Name'},
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.first_name == 'Updated'
    assert user.last_name == 'Name'


def test_change_password_view(api_client, create_user):
    user = create_user(email='changepw@example.com', username='changepw', password='OldPass123')
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse('change_password'),
        {
            'old_password': 'OldPass123',
            'new_password': 'NewStrongPass123',
            'new_password_confirm': 'NewStrongPass123',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.check_password('NewStrongPass123') is True


def test_password_reset_request_view_sends_email(monkeypatch, api_client, create_user):
    create_user(email='reset@example.com', username='resetuser')
    send_mail_calls = {}

    def fake_send_mail(*args, **kwargs):
        send_mail_calls['called'] = True
        return 1

    monkeypatch.setattr('accounts.api.views.send_mail', fake_send_mail)

    response = api_client.post(
        reverse('password_reset'), {'email': 'reset@example.com'}, format='json'
    )

    assert response.status_code == status.HTTP_200_OK
    assert send_mail_calls.get('called') is True


def test_password_reset_confirm_view_sets_new_password(api_client, create_user):
    user = create_user(email='confirm@example.com', username='confirmuser', password='OldPass123')
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    response = api_client.post(
        reverse('password_reset_confirm'),
        {
            'uid': uid,
            'token': token,
            'new_password': 'NewStrongPass123',
            'new_password_confirm': 'NewStrongPass123',
        },
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.check_password('NewStrongPass123') is True


def test_logout_view_blacklists_token(monkeypatch, api_client, create_user):
    user = create_user(email='logout@example.com', username='logoutuser')
    api_client.force_authenticate(user=user)

    refresh = RefreshToken.for_user(user)

    # Ensure blacklist works even if blacklist app is not installed
    monkeypatch.setattr(RefreshToken, 'blacklist', lambda self: None, raising=False)

    response = api_client.post(reverse('logout'), {'refresh': str(refresh)}, format='json')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == 'Logout successful'
