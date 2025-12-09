import pytest

pytestmark = pytest.mark.django_db


def test_str_returns_name(create_category):
    category = create_category(name='Data Science')

    assert str(category) == 'Data Science'


def test_category_defaults_active(create_category):
    category = create_category()

    assert category.is_active is True
