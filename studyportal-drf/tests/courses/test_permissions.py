import pytest

from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from courses.api.permissions import IsInstructorOrReadOnly, IsStudent

pytestmark = pytest.mark.django_db


factory = APIRequestFactory()


def _request(method: str, user=None):
    request = getattr(factory, method.lower())('/')
    request.user = user
    return request


def test_safe_methods_allow_any_user():
    permission = IsInstructorOrReadOnly()
    request = _request('get', AnonymousUser())

    assert permission.has_permission(request, view=None) is True


def test_write_denied_for_non_instructors(create_user):
    permission = IsInstructorOrReadOnly()
    student = create_user(email='student@example.com', username='student', role='student')
    request = _request('post', student)

    assert permission.has_permission(request, view=None) is False


def test_write_allowed_for_instructors(create_user):
    permission = IsInstructorOrReadOnly()
    instructor = create_user(
        email='instructor@example.com', username='instructor', role='instructor'
    )
    request = _request('post', instructor)

    assert permission.has_permission(request, view=None) is True


def test_object_permission_allows_owner(create_course, create_user):
    permission = IsInstructorOrReadOnly()
    course = create_course()
    request = _request('patch', course.instructor)

    assert permission.has_object_permission(request, view=None, obj=course) is True


def test_object_permission_denies_other_instructor(create_course, create_user):
    permission = IsInstructorOrReadOnly()
    course = create_course()
    other_instructor = create_user(email='other@example.com', username='other', role='instructor')
    request = _request('patch', other_instructor)

    assert permission.has_object_permission(request, view=None, obj=course) is False


def test_object_permission_allows_safe_method(create_course, create_user):
    permission = IsInstructorOrReadOnly()
    course = create_course()
    student = create_user(email='student2@example.com', username='student2', role='student')
    request = _request('get', student)

    assert permission.has_object_permission(request, view=None, obj=course) is True


def test_is_student_allows_students_only(create_user):
    permission = IsStudent()
    student = create_user(email='student3@example.com', username='student3', role='student')
    instructor = create_user(
        email='instructor2@example.com', username='instructor2', role='instructor'
    )

    assert permission.has_permission(_request('get', student), view=None) is True
    assert permission.has_permission(_request('get', instructor), view=None) is False
