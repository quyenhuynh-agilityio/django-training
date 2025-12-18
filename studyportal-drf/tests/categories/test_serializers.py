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


def test_category_serializer_rejects_empty_name():
    serializer = CategorySerializer(data={'name': '   '})
    assert serializer.is_valid() is False
    assert 'name' in serializer.errors
    # Test with actual empty string after stripping
    serializer2 = CategorySerializer(data={'name': ''})
    assert serializer2.is_valid() is False
    assert 'name' in serializer2.errors


def test_category_serializer_rejects_duplicate_name(create_category):
    create_category(name='Backend')
    serializer = CategorySerializer(data={'name': 'Backend'})
    assert serializer.is_valid() is False
    assert 'name' in serializer.errors


def test_category_serializer_allows_same_name_on_update(create_category):
    category = create_category(name='Backend')
    serializer = CategorySerializer(instance=category, data={'name': 'Backend'})
    assert serializer.is_valid(), serializer.errors


def test_category_serializer_strips_whitespace(create_category):
    serializer = CategorySerializer(data={'name': '  Frontend  '})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['name'] == 'Frontend'
