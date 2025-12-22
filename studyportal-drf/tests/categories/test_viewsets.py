import pytest

from rest_framework import status

pytestmark = pytest.mark.django_db


def test_category_list_viewset(api_client, create_category):
    """Test listing categories"""
    create_category(name='Backend')
    create_category(name='Frontend')

    response = api_client.get('/api/v1/categories/')

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) == 2


def test_category_retrieve_viewset(api_client, create_category):
    """Test retrieving a single category"""
    category = create_category(name='Backend')

    response = api_client.get(f'/api/v1/categories/{category.id}/')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == 'Backend'
