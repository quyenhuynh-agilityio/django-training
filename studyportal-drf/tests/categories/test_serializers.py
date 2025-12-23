# tests/categories/test_serializers.py
import pytest

from categories.api.serializers import CategorySerializer

pytestmark = pytest.mark.django_db


def test_category_serializer_outputs_expected_fields(create_category):
    """Direct serializer test - outputs snake_case"""
    category = create_category(name='Backend')

    data = CategorySerializer(category).data

    assert data['id'] == str(category.id)
    assert data['name'] == 'Backend'
    assert data['is_active'] is True  # snake_case in direct serializer test
    assert 'created_at' in data and 'updated_at' in data  # snake_case


def test_category_serializer_accepts_snake_case_input():
    """Direct serializer test - accepts snake_case"""
    serializer = CategorySerializer(data={'name': 'Backend', 'is_active': False})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['is_active'] is False


def test_category_serializer_rejects_empty_name():
    """Test that empty or whitespace-only names are rejected"""
    # Whitespace-only string
    serializer = CategorySerializer(data={'name': '   '})
    assert serializer.is_valid() is False
    assert 'name' in serializer.errors

    # Empty string
    serializer2 = CategorySerializer(data={'name': ''})
    assert serializer2.is_valid() is False
    assert 'name' in serializer2.errors


def test_category_serializer_rejects_missing_name():
    """Test that name field is required"""
    serializer = CategorySerializer(data={})
    assert serializer.is_valid() is False
    assert 'name' in serializer.errors


def test_category_serializer_rejects_duplicate_name(create_category):
    """Test that duplicate category names are not allowed"""
    create_category(name='Backend')
    serializer = CategorySerializer(data={'name': 'Backend'})
    assert serializer.is_valid() is False
    assert 'name' in serializer.errors


def test_category_serializer_allows_same_name_on_update(create_category):
    """Test that updating a category with its own name is allowed"""
    category = create_category(name='Backend')
    serializer = CategorySerializer(instance=category, data={'name': 'Backend'})
    assert serializer.is_valid(), serializer.errors


def test_category_serializer_strips_whitespace():
    """Test that leading/trailing whitespace is stripped from name"""
    serializer = CategorySerializer(data={'name': '  Frontend  '})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['name'] == 'Frontend'


def test_category_serializer_case_insensitive_duplicate(create_category):
    """Test that duplicate detection is case-insensitive"""
    create_category(name='Backend')
    serializer = CategorySerializer(data={'name': 'backend'})
    assert serializer.is_valid() is False
    assert 'name' in serializer.errors
