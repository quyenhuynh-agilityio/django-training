import pytest

from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


def test_full_name_with_names(create_user):
    user = create_user(first_name='Jane', last_name='Doe')
    assert user.full_name == 'Jane Doe'


def test_full_name_falls_back_to_email_prefix(create_user):
    user = create_user(first_name='', last_name='', email='student@example.com')
    assert user.full_name == 'student'


def test_role_helpers(create_user):
    student = create_user(email='s@example.com', username='student1', role='student')
    instructor = create_user(email='i@example.com', username='instructor1', role='instructor')

    assert student.is_student is True
    assert instructor.is_instructor is True


def test_clean_lowercases_email(create_user):
    user_model = get_user_model()
    user = user_model(email='UPPER@EXAMPLE.COM', username='upper')

    user.clean()

    assert user.email == 'upper@example.com'
