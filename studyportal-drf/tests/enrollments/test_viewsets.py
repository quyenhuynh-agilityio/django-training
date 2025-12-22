import pytest

from rest_framework import status

from courses.models import Course
from enrollments.models import Enrollment

pytestmark = pytest.mark.django_db


def test_enrollment_list_viewset(api_client, create_user, create_course, create_enrollment):
    """Test listing student's enrollments"""
    student = create_user(email='student@example.com', username='student', role='student')
    course = create_course()
    create_enrollment(student=student, course=course)

    api_client.force_authenticate(user=student)
    response = api_client.get('/api/v1/enrollments/students/enrollments/')

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) == 1


def test_enrollment_retrieve_viewset(api_client, create_user, create_enrollment):
    """Test retrieving a single enrollment"""
    student = create_user(email='student@example.com', username='student', role='student')
    enrollment = create_enrollment(student=student)

    api_client.force_authenticate(user=student)
    response = api_client.get(f'/api/v1/enrollments/students/enrollments/{enrollment.id}/')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['course']['title'] == enrollment.course.title


def test_enrollment_enroll_action(api_client, create_user, create_course):
    """Test enrolling in a course"""
    student = create_user(email='student@example.com', username='student', role='student')
    course = create_course(status=Course.STATUS_ACTIVE, is_active=True)

    api_client.force_authenticate(user=student)
    response = api_client.post(
        '/api/v1/enrollments/students/enrollments/enroll/',
        {'course_id': str(course.id)},
        format='json',
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert 'Successfully enrolled' in response.data['message']


def test_enrollment_enroll_duplicate(api_client, create_user, create_course, create_enrollment):
    """Test that duplicate enrollment is rejected"""
    student = create_user(email='student@example.com', username='student', role='student')
    course = create_course(status=Course.STATUS_ACTIVE, is_active=True)
    create_enrollment(student=student, course=course)

    api_client.force_authenticate(user=student)
    response = api_client.post(
        '/api/v1/enrollments/students/enrollments/enroll/',
        {'course_id': str(course.id)},
        format='json',
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_enrollment_leave_action(api_client, create_user, create_enrollment):
    """Test leaving a course"""
    student = create_user(email='student@example.com', username='student', role='student')
    enrollment = create_enrollment(student=student)

    api_client.force_authenticate(user=student)
    response = api_client.delete(f'/api/v1/enrollments/students/enrollments/{enrollment.id}/leave/')

    assert response.status_code == status.HTTP_200_OK
    assert 'Successfully left' in response.data['message']

    enrollment.refresh_from_db()
    assert enrollment.is_active is False
    assert enrollment.status == Enrollment.STATUS_DROPPED


def test_enrollment_swagger_fake_view(api_client, create_user):
    """Test that swagger_fake_view returns empty queryset"""
    from enrollments.api.views import StudentEnrolledCoursesViewSet

    student = create_user(email='student@example.com', username='student', role='student')
    api_client.force_authenticate(user=student)

    viewset = StudentEnrolledCoursesViewSet()
    viewset.swagger_fake_view = True
    viewset.request = api_client.request()

    queryset = viewset.get_queryset()
    assert queryset.count() == 0
