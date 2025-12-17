import pytest

from django.core.exceptions import ValidationError

from courses.models import Course

pytestmark = pytest.mark.django_db


def test_can_enroll_only_when_active_and_not_full(create_course, create_enrollment, create_user):
    course = create_course(max_students=1, status=Course.STATUS_ACTIVE, is_active=True)

    assert course.can_enroll() is True

    # Fill the course to capacity
    create_enrollment(
        student=create_user(email='student1@example.com', username='student1', role='student'),
        course=course,
    )
    course.refresh_from_db()

    assert course.is_full is True
    assert course.can_enroll() is False


def test_clean_rejects_non_instructor_instructor(create_user):
    student_user = create_user(email='student@example.com', username='studentuser', role='student')

    with pytest.raises(ValidationError):
        Course.objects.create(
            title='Invalid Instructor Course',
            course_code='INV101',
            instructor=student_user,
            status=Course.STATUS_ACTIVE,
        )


def test_prevent_disabling_in_progress_course_with_students(
    create_course, create_enrollment, create_user
):
    course = create_course(status=Course.STATUS_ACTIVE, is_active=True)
    student = create_user(email='student2@example.com', username='student2', role='student')
    create_enrollment(student=student, course=course)

    # Move course to in-progress state (allowed)
    course.status = Course.STATUS_IN_PROGRESS
    course.save()

    # Disabling should now be blocked
    course.is_active = False
    with pytest.raises(ValidationError):
        course.save()


def test_soft_delete_marks_inactive(create_course):
    course = create_course()

    course.soft_delete()
    course.refresh_from_db()

    assert course.is_active is False


def test_str_and_is_full_without_max_students(create_course):
    course = create_course(title='APIs', course_code='API500', max_students=None)

    assert str(course) == 'API500 - APIs'
    assert course.is_full is False
