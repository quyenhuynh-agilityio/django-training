import pytest

from rest_framework import serializers

from courses.api.serializers import (
    CourseCreateUpdateSerializer,
    CourseDeleteResponseSerializer,
    CourseDetailSerializer,
    EnrolledStudentsResponseSerializer,
    PaginatedResponseSerializer,
)
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
    # Create course in ACTIVE status first (required for enrollment)
    course = create_course(status=Course.STATUS_ACTIVE, is_active=True)
    student = create_user(email='enrolled@example.com', username='enrolled', role='student')
    # Create enrollment while course is active
    create_enrollment(student=student, course=course)
    # Change course to IN_PROGRESS status (simulating course starting)
    course.status = Course.STATUS_IN_PROGRESS
    course.save()

    serializer = CourseCreateUpdateSerializer(
        instance=course,
        data={'is_active': False},
        partial=True,
    )

    with pytest.raises(serializers.ValidationError):
        serializer.is_valid(raise_exception=True)


def test_course_detail_serializer_category_names(create_category, create_course):
    """Test that category names are properly formatted"""
    categories = [create_category(name='Backend'), create_category(name='API')]
    course = create_course()
    course.categories.set(categories)

    serializer = CourseDetailSerializer(course)

    # Direct serializer test returns snake_case
    assert serializer.data['category_names'] == 'API, Backend'


def test_course_code_empty_validation():
    """Test that empty course code is rejected"""
    serializer = CourseCreateUpdateSerializer(data={'title': 'Test Course', 'course_code': '   '})
    assert serializer.is_valid() is False
    assert 'course_code' in serializer.errors


def test_course_code_invalid_format():
    """Test that invalid course code format is rejected"""
    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test Course', 'course_code': 'INVALID@CODE!'}
    )
    assert serializer.is_valid() is False
    assert 'course_code' in serializer.errors


def test_course_code_uppercase_normalization(create_user):
    """Test that course code is normalized to uppercase"""
    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test Course', 'course_code': 'lower123'}
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['course_code'] == 'LOWER123'


def test_validate_max_students_null_allowed():
    """Test that max_students can be null"""
    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Unlimited Course', 'course_code': 'UNL100', 'max_students': None}
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['max_students'] is None


def test_validate_max_students_negative():
    """Test that negative max_students is rejected"""
    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Bad Course', 'course_code': 'BAD100', 'max_students': -1}
    )
    assert serializer.is_valid() is False
    assert 'max_students' in serializer.errors


def test_validate_status_invalid():
    """Test that invalid status is rejected"""
    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test Course', 'course_code': 'TST100', 'status': 'invalid_status'}
    )
    assert serializer.is_valid() is False
    assert 'status' in serializer.errors


def test_validate_video_url_invalid():
    """Test that invalid video URL format is rejected"""
    serializer = CourseCreateUpdateSerializer(
        data={
            'title': 'Test Course',
            'course_code': 'TST100',
            'video_url': 'not-a-valid-url',
        }
    )
    assert serializer.is_valid() is False
    assert 'video_url' in serializer.errors


def test_validate_video_url_valid():
    """Test that valid video URL is accepted"""
    serializer = CourseCreateUpdateSerializer(
        data={
            'title': 'Test Course',
            'course_code': 'TST100',
            'video_url': 'https://www.youtube.com/watch?v=test',
        }
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['video_url'] == 'https://www.youtube.com/watch?v=test'


def test_validate_image_url_invalid():
    """Test that invalid image URL format is rejected"""
    serializer = CourseCreateUpdateSerializer(
        data={
            'title': 'Test Course',
            'course_code': 'TST100',
            'image_url': 'not-a-valid-url',
        }
    )
    assert serializer.is_valid() is False
    assert 'image_url' in serializer.errors


def test_validate_image_url_valid():
    """Test that valid image URL is accepted"""
    serializer = CourseCreateUpdateSerializer(
        data={
            'title': 'Test Course',
            'course_code': 'TST100',
            'image_url': 'https://example.com/image.jpg',
        }
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['image_url'] == 'https://example.com/image.jpg'


def test_validate_category_ids_empty_list():
    """Test that empty category_ids list is allowed"""
    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test Course', 'course_code': 'TST100', 'category_ids': []}
    )
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['category_ids'] == []


def test_validate_category_ids_duplicates_removed(create_category):
    """Test that duplicate category IDs are removed"""
    category = create_category(name='Test')
    serializer = CourseCreateUpdateSerializer(
        data={
            'title': 'Test Course',
            'course_code': 'TST100',
            'category_ids': [category.id, category.id, category.id],
        }
    )
    assert serializer.is_valid(), serializer.errors
    # Should have only one unique ID
    assert len(serializer.validated_data['category_ids']) == 1


def test_course_code_validation_empty():
    """Test course code validation rejects empty codes"""

    serializer = CourseCreateUpdateSerializer(data={'title': 'Test', 'course_code': ''})
    assert serializer.is_valid() is False
    assert 'course_code' in serializer.errors


def test_course_code_validation_whitespace():
    """Test course code validation rejects whitespace-only codes"""

    serializer = CourseCreateUpdateSerializer(data={'title': 'Test', 'course_code': '   '})
    assert serializer.is_valid() is False
    assert 'course_code' in serializer.errors


def test_course_code_validation_invalid_chars():
    """Test course code validation rejects invalid characters"""

    serializer = CourseCreateUpdateSerializer(data={'title': 'Test', 'course_code': 'CODE@123'})
    assert serializer.is_valid() is False
    assert 'course_code' in serializer.errors


def test_course_code_normalization():
    """Test course code is normalized to uppercase"""

    serializer = CourseCreateUpdateSerializer(data={'title': 'Test', 'course_code': 'code123'})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['course_code'] == 'CODE123'


def test_max_students_validation_negative():
    """Test max_students validation rejects negative values"""

    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test', 'course_code': 'TEST001', 'max_students': -1}
    )
    assert serializer.is_valid() is False
    assert 'max_students' in serializer.errors


def test_max_students_validation_zero():
    """Test max_students validation rejects zero"""

    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test', 'course_code': 'TEST001', 'max_students': 0}
    )
    assert serializer.is_valid() is False
    assert 'max_students' in serializer.errors


def test_status_validation_invalid():
    """Test status validation rejects invalid status"""

    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test', 'course_code': 'TEST001', 'status': 'invalid'}
    )
    assert serializer.is_valid() is False
    assert 'status' in serializer.errors


def test_video_url_validation_invalid_scheme():
    """Test video URL validation rejects invalid schemes"""

    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test', 'course_code': 'TEST001', 'video_url': 'ftp://example.com/video.mp4'}
    )
    assert serializer.is_valid() is False
    assert 'video_url' in serializer.errors


def test_image_url_validation_invalid_scheme():
    """Test image URL validation rejects invalid schemes"""

    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test', 'course_code': 'TEST001', 'image_url': 'ftp://example.com/image.jpg'}
    )
    assert serializer.is_valid() is False
    assert 'image_url' in serializer.errors


def test_validate_max_students_zero():
    """Test max_students validation rejects zero"""

    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test', 'course_code': 'TEST001', 'max_students': 0}
    )
    assert serializer.is_valid() is False
    assert 'max_students' in serializer.errors


def test_validate_video_url_invalid_scheme():
    """Test video URL validation rejects invalid schemes"""

    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test', 'course_code': 'TEST001', 'video_url': 'ftp://example.com/video.mp4'}
    )
    assert serializer.is_valid() is False
    assert 'video_url' in serializer.errors


def test_validate_image_url_invalid_scheme():
    """Test image URL validation rejects invalid schemes"""

    serializer = CourseCreateUpdateSerializer(
        data={'title': 'Test', 'course_code': 'TEST001', 'image_url': 'ftp://example.com/image.jpg'}
    )
    assert serializer.is_valid() is False
    assert 'image_url' in serializer.errors


def test_paginated_response_validate_count_negative():
    """Test PaginatedResponseSerializer rejects negative count"""

    serializer = PaginatedResponseSerializer(data={'count': -1})
    assert serializer.is_valid() is False
    assert 'count' in serializer.errors


def test_enrolled_students_request_validate_message_empty():
    """Test CourseDeleteResponseSerializer rejects empty message"""
    serializer = CourseDeleteResponseSerializer(
        data={
            'message': '',
            'course_id': '12345678-1234-5678-9012-123456789012',
            'course_code': 'TEST001',
        }
    )
    assert serializer.is_valid() is False
    assert 'message' in serializer.errors


def test_enrolled_students_request_validate_course_code_empty():
    """Test CourseDeleteResponseSerializer rejects empty course_code"""

    serializer = CourseDeleteResponseSerializer(
        data={
            'message': 'Test message',
            'course_id': '12345678-1234-5678-9012-123456789012',
            'course_code': '',
        }
    )
    assert serializer.is_valid() is False
    assert 'course_code' in serializer.errors


def test_enrolled_students_response_validate_results_not_list():
    """Test EnrolledStudentsResponseSerializer rejects non-list results"""
    serializer = EnrolledStudentsResponseSerializer(data={'count': 0, 'results': 'not_a_list'})
    assert serializer.is_valid() is False
    assert 'results' in serializer.errors
