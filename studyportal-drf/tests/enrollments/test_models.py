import pytest

from django.core.exceptions import ValidationError

from courses.models import Course
from enrollments.models import Enrollment

pytestmark = pytest.mark.django_db


def test_clean_rejects_non_student_role(create_course, create_user):
    instructor_user = create_user(
        email='teacher@example.com', username='teacher', role='instructor'
    )
    course = create_course(instructor=instructor_user)

    with pytest.raises(ValidationError):
        Enrollment.objects.create(student=instructor_user, course=course)


def test_clean_blocks_full_course(create_course, create_enrollment, create_user):
    course = create_course(max_students=1, status=Course.STATUS_ACTIVE)
    first_student = create_user(email='first@example.com', username='first', role='student')
    second_student = create_user(email='second@example.com', username='second', role='student')

    create_enrollment(student=first_student, course=course)

    with pytest.raises(ValidationError):
        Enrollment.objects.create(student=second_student, course=course)


def test_unenroll_sets_dropped_status(create_enrollment):
    enrollment = create_enrollment()

    enrollment.unenroll()
    enrollment.refresh_from_db()

    assert enrollment.is_active is False
    assert enrollment.status == Enrollment.STATUS_DROPPED


def test_clean_blocks_inactive_course(create_course, create_user):
    inactive_course = create_course(is_active=False)
    student = create_user(
        email='inactivecourse@example.com', username='inactivecourse', role='student'
    )

    with pytest.raises(ValidationError, match='not active'):
        Enrollment.objects.create(student=student, course=inactive_course)
