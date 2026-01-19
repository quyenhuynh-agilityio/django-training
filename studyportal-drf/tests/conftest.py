import uuid

import pytest

from tests import factories


@pytest.fixture
def api_client():
    """DRF API client fixture."""
    from rest_framework.test import APIClient

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
        from django.contrib.auth import get_user_model

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


@pytest.fixture
def create_category():
    """Factory to create categories."""

    def _create_category(name=None, **extra):
        from categories.models import Category

        return Category.objects.create(name=name or f'Category-{uuid.uuid4().hex[:8]}', **extra)

    return _create_category


@pytest.fixture
def create_course(create_user, create_category):
    """Factory to create courses with default active instructor."""

    def _create_course(
        title='Sample Course',
        course_code='CRS101',
        instructor=None,
        status=None,
        is_active=True,
        max_students=None,
        categories=None,
        **extra,
    ):
        from courses.models import Course

        if status is None:
            status = Course.STATUS_ACTIVE
        instructor = instructor or create_user(
            email=f'instructor-{uuid.uuid4().hex[:6]}@example.com',
            username=f'instructor-{uuid.uuid4().hex[:6]}',
            role='instructor',
        )
        course = Course.objects.create(
            title=title,
            course_code=course_code,
            instructor=instructor,
            status=status,
            is_active=is_active,
            max_students=max_students,
            **extra,
        )
        if categories:
            course.categories.set(categories)
        return course

    return _create_course


@pytest.fixture
def create_enrollment(create_user, create_course):
    """Factory to create enrollments."""

    def _create_enrollment(student=None, course=None, **extra):
        from enrollments.models import Enrollment

        student = student or create_user(
            email=f'student-{uuid.uuid4().hex[:6]}@example.com',
            username=f'student-{uuid.uuid4().hex[:6]}',
            role='student',
        )
        course = course or create_course()
        return Enrollment.objects.create(student=student, course=course, **extra)

    return _create_enrollment


# ============================================================================
# Factory Boy Fixtures
# ============================================================================
# These fixtures provide factory_boy factories for more flexible test data
# generation. They coexist with the above function-based fixtures.


@pytest.fixture
def user_factory():
    """Provides UserFactory for creating users with factory_boy."""
    return factories.UserFactory


@pytest.fixture
def student_factory():
    """Provides StudentFactory for creating student users."""
    return factories.StudentFactory


@pytest.fixture
def instructor_factory():
    """Provides InstructorFactory for creating instructor users."""
    return factories.InstructorFactory


@pytest.fixture
def category_factory():
    """Provides CategoryFactory for creating categories."""
    return factories.CategoryFactory


@pytest.fixture
def course_factory():
    """Provides CourseFactory for creating courses."""
    return factories.CourseFactory


@pytest.fixture
def enrollment_factory():
    """Provides EnrollmentFactory for creating enrollments."""
    return factories.EnrollmentFactory
