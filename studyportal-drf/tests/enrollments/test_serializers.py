import pytest

from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from courses.models import Course
from enrollments.api.serializers import EnrollmentCreateSerializer
from enrollments.models import Enrollment

pytestmark = pytest.mark.django_db


def _build_request(user):
    factory = APIRequestFactory()
    request = factory.post('/api/enrollments/')
    request.user = user
    return request


def test_validate_course_id_must_exist(create_user):
    student = create_user(email='student@example.com', username='student', role='student')
    request = _build_request(student)

    serializer = EnrollmentCreateSerializer(
        data={'course_id': '00000000-0000-0000-0000-000000000000'},
        context={'request': request},
    )

    assert serializer.is_valid() is False
    assert 'course_id' in serializer.errors


def test_prevent_enrollment_in_inactive_course(create_course, create_user):
    course = create_course(is_active=False)
    student = create_user(email='inactive@example.com', username='inactive', role='student')
    request = _build_request(student)

    serializer = EnrollmentCreateSerializer(
        data={'course_id': course.id},
        context={'request': request},
    )

    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_prevent_duplicate_active_enrollment(create_course, create_enrollment, create_user):
    course = create_course()
    student = create_user(email='dup@example.com', username='dup', role='student')
    create_enrollment(student=student, course=course)
    request = _build_request(student)

    serializer = EnrollmentCreateSerializer(
        data={'course_id': course.id},
        context={'request': request},
    )

    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_create_enrollment_success(create_course, create_user):
    course = create_course()
    student = create_user(email='new@example.com', username='new', role='student')
    request = _build_request(student)

    serializer = EnrollmentCreateSerializer(
        data={'course_id': course.id},
        context={'request': request},
    )
    assert serializer.is_valid(), serializer.errors

    enrollment = serializer.save()

    assert isinstance(enrollment, Enrollment)
    assert enrollment.student == student
    assert enrollment.course == course


def test_prevent_enrollment_in_non_active_status(create_course, create_user):
    course = create_course(status=Course.STATUS_IN_PROGRESS)
    student = create_user(email='progress@example.com', username='progress', role='student')
    request = _build_request(student)

    serializer = EnrollmentCreateSerializer(
        data={'course_id': course.id},
        context={'request': request},
    )

    with pytest.raises(serializers.ValidationError, match='in progress'):
        serializer.is_valid(raise_exception=True)


def test_prevent_enrollment_when_course_full(create_course, create_enrollment, create_user):
    course = create_course(max_students=1)
    first_student = create_user(email='firstfull@example.com', username='firstfull', role='student')
    create_enrollment(student=first_student, course=course)

    second_student = create_user(
        email='secondfull@example.com', username='secondfull', role='student'
    )
    request = _build_request(second_student)

    serializer = EnrollmentCreateSerializer(
        data={'course_id': course.id},
        context={'request': request},
    )

    with pytest.raises(serializers.ValidationError, match='maximum capacity'):
        serializer.is_valid(raise_exception=True)
