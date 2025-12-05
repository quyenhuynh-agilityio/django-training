import pytest

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """DRF API client fixture."""
    return APIClient()


@pytest.fixture
def create_user():
    """Factory to create a user with sensible defaults."""

    def _create_user(
        email='user@example.com',
        username='user',
        first_name='Test',
        last_name='User',
        password='StrongPass123',
        **extra,
    ):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
            **extra,
        )
        return user

    return _create_user
