import pytest
from rest_framework_simplejwt.tokens import RefreshToken

from django.test import override_settings
from rest_framework import status

pytestmark = pytest.mark.django_db


def test_auth_logout_requires_authentication(api_client):
    response = api_client.post(
        '/api/v1/users/auth/logout/',
        {'refresh': 'anything'},
        format='json',
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_auth_logout_requires_refresh_field(api_client, create_user):
    user = create_user(email='student@example.com', username='student', role='student')
    api_client.force_authenticate(user=user)

    response = api_client.post('/api/v1/users/auth/logout/', {}, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['errors']['message'] == ['Logout failed']
    assert response.data['errors']['code']['refresh'] == ['This field is required.']


def test_auth_logout_rejects_invalid_refresh_token(api_client, create_user):
    user = create_user(email='student@example.com', username='student', role='student')
    api_client.force_authenticate(user=user)

    response = api_client.post(
        '/api/v1/users/auth/logout/',
        {'refresh': 'not-a-token'},
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['errors']['message'] == ['Logout failed']
    assert response.data['errors']['code']['refresh'] == ['Token is invalid or expired']


def test_auth_logout_success_warns_when_blacklist_app_missing(api_client, create_user):
    user = create_user(email='student@example.com', username='student', role='student')
    api_client.force_authenticate(user=user)

    refresh = str(RefreshToken.for_user(user))

    response = api_client.post(
        '/api/v1/users/auth/logout/',
        {'refresh': refresh},
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == 'Logout successful'
    # In this project, token_blacklist isn't installed in settings, so logout returns a warning.
    assert 'warning' in response.data


@override_settings(
    PASSWORD_RESET_DEBUG_EXPOSE_TOKENS=True,
    PASSWORD_RESET_DISABLE_EMAIL=True,
    FRONTEND_URL='http://localhost:3000',
)
def test_auth_password_reset_exposes_debug_tokens_when_enabled(api_client, create_user):
    create_user(email='reset@example.com', username='resetuser', is_active=True)

    response = api_client.post(
        '/api/v1/users/auth/password-reset/',
        {'email': 'reset@example.com'},
        format='json',
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == (
        'If an account exists with this email, a password reset link has been sent.'
    )

    debug = response.data.get('debug')
    assert debug is not None
    assert set(debug.keys()) == {'uid', 'token', 'reset_link'}
    assert '/reset-password/' in debug['reset_link']
