import pytest

from categories.api.serializers import CategorySerializer

pytestmark = pytest.mark.django_db


def test_category_serializer_outputs_expected_fields(create_category):
    category = create_category(name='Backend')

    data = CategorySerializer(category).data

    assert data['id'] == str(category.id)
    assert data['name'] == 'Backend'
    assert data['is_active'] is True
    assert 'created_at' in data and 'updated_at' in data
