import pytest

from rest_framework import serializers

from courses.api.serializers import CourseCreateUpdateSerializer, CourseDetailSerializer
from courses.models import Course

pytestmark = pytest.mark.django_db


def test_course_code_is_uppercased_and_unique(create_course):
    create_course(course_code='CRS101')
    payload = {
        'title': 'New Course',
        'course_code': 'crs101',
        'description': 'Duplicate code',
    }

    serializer = CourseCreateUpdateSerializer(data=payload)

    assert serializer.is_valid() is False
    assert 'course_code' in serializer.errors


def test_validate_category_ids_rejects_invalid_id(create_category):
    good_category = create_category(name='Valid')
    serializer = CourseCreateUpdateSerializer(
        data={
            'title': 'Invalid Category Course',
            'course_code': 'CAT404',
            'category_ids': [good_category.id, '00000000-0000-0000-0000-000000000000'],
        }
    )

    assert serializer.is_valid() is False
    assert 'category_ids' in serializer.errors


def test_validate_category_ids_and_create_sets_relations(create_category, create_user):
    categories = [create_category(name='Backend'), create_category(name='Data')]
    instructor = create_user(
        email='instructor-api@example.com', username='instructor-api', role='instructor'
    )
    payload = {
        'title': 'API Design',
        'course_code': 'API200',
        'category_ids': [cat.id for cat in categories],
    }

    serializer = CourseCreateUpdateSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors

    course = serializer.save(instructor=instructor)

    assert set(course.categories.values_list('name', flat=True)) == {'Backend', 'Data'}


def test_update_sets_categories_and_upcases_code(create_category, create_course):
    category = create_category(name='Initial')
    new_category = create_category(name='Updated')
    course = create_course(course_code='LOW100')
    course.categories.set([category])

    serializer = CourseCreateUpdateSerializer(
        instance=course,
        data={'course_code': 'upd200', 'category_ids': [new_category.id]},
        partial=True,
    )
    assert serializer.is_valid(), serializer.errors

    updated = serializer.save()
    assert updated.course_code == 'UPD200'
    assert list(updated.categories.values_list('name', flat=True)) == ['Updated']


def test_validate_max_students_positive_number():
    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Bad Capacity', 'course_code': 'CAP100', 'max_students': 0}
    )

    assert serializer.is_valid() is False
    assert 'max_students' in serializer.errors


def test_prevent_disabling_in_progress_with_enrollments(
    create_course, create_enrollment, create_user
):
    course = create_course(status=Course.STATUS_IN_PROGRESS, is_active=True)
    student = create_user(email='enrolled@example.com', username='enrolled', role='student')
    create_enrollment(student=student, course=course)

    serializer = CourseCreateUpdateSerializer(
        instance=course,
        data={'is_active': False},
        partial=True,
    )

    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_course_detail_serializer_category_names(create_category, create_course):
    categories = [create_category(name='Backend'), create_category(name='API')]
    course = create_course()
    course.categories.set(categories)

    serializer = CourseDetailSerializer(course)

    assert serializer.data['category_names'] == 'API, Backend'
