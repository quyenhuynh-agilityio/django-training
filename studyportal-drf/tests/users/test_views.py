import pytest

from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_user_login_view_get(client):
    """Test user login view GET request"""
    response = client.get(reverse('login'))

    assert response.status_code == 200
    assert 'form' in response.context
    assert response.templates[0].name == 'users/login.html'


def test_user_login_view_post_valid_credentials(client, create_user):
    """Test user login view POST with valid credentials"""
    response = client.post(
        reverse('login'),
        {'username': 'login@example.com', 'password': 'StrongPass123'},
    )

    # Should redirect to homepage
    assert response.status_code == 302
    assert response.url == '/'


def test_user_login_view_post_invalid_credentials(client, create_user):
    """Test user login view POST with invalid credentials"""
    create_user(email='login@example.com', username='loginuser', password='StrongPass123')

    response = client.post(
        reverse('login'),
        {'username': 'login@example.com', 'password': 'WrongPassword'},
    )

    # Should render form with errors
    assert response.status_code == 200
    assert 'form' in response.context
    assert response.context['form'].errors


def test_user_login_view_post_nonexistent_user(client):
    """Test user login view POST with nonexistent user"""
    response = client.post(
        reverse('login'),
        {'username': 'nonexistent@example.com', 'password': 'SomePassword'},
    )

    # Should render form with errors
    assert response.status_code == 200
    assert 'form' in response.context
    assert response.context['form'].errors


def test_user_logout_view(client, create_user):
    """Test user logout view"""
    user = create_user(email='logout@example.com', username='logoutuser')
    client.force_login(user)

    # Verify user is logged in
    assert client.session.get('_auth_user_id') == str(user.id)

    response = client.get(reverse('logout'))

    # Should redirect to homepage
    assert response.status_code == 302
    assert response.url == '/'
    # Verify user is logged out
    assert '_auth_user_id' not in client.session


def test_user_logout_view_anonymous(client):
    """Test user logout view for anonymous user"""
    response = client.get(reverse('logout'))

    # Should still redirect (logout works for anonymous too)
    assert response.status_code == 302
    assert response.url == '/'
