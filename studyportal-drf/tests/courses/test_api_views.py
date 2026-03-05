"""Tests for Course API ViewSet (courses.api.views)."""

import uuid

import pytest

from rest_framework import status

from courses.models import Course

pytestmark = pytest.mark.django_db


def test_course_list_anonymous(api_client, create_course):
    """Anonymous users can list active courses."""
    create_course(course_code='PUB1', is_active=True)
    response = api_client.get('/api/v1/courses/')
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data
    assert response.data['count'] >= 1


def test_course_list_authenticated(api_client, create_user, create_course):
    """Authenticated users can list active courses."""
    user = create_user(email='u1@example.com', username='u1')
    create_course(course_code='PUB2', is_active=True)
    api_client.force_authenticate(user=user)
    response = api_client.get('/api/v1/courses/')
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data


def test_course_list_my_courses_instructor(api_client, create_user, create_course):
    """Instructor with my_courses=true sees only own courses."""
    instructor = create_user(
        email='inst@example.com', username='inst', role='instructor'
    )
    other = create_user(email='other@example.com', username='other', role='instructor')
    my_course = create_course(
        course_code='MINE', instructor=instructor, is_active=True
    )
    create_course(course_code='OTHER', instructor=other, is_active=True)

    api_client.force_authenticate(user=instructor)
    response = api_client.get('/api/v1/courses/?my_courses=true')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['count'] == 1
    assert response.data['results'][0]['course_code'] == 'MINE'


def test_course_retrieve(api_client, create_course):
    """Anyone can retrieve a single active course."""
    course = create_course(course_code='RET1', is_active=True)
    response = api_client.get(f'/api/v1/courses/{course.id}/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['course_code'] == 'RET1'
    assert 'enrolled_count' in response.data or 'id' in response.data


def test_course_create_as_instructor(api_client, create_user, create_category):
    """Instructor can create a course."""
    instructor = create_user(
        email='ci@example.com', username='ci', role='instructor'
    )
    category = create_category(name='Cat1')
    api_client.force_authenticate(user=instructor)
    response = api_client.post(
        '/api/v1/courses/',
        {
            'title': 'New Course',
            'course_code': 'NEW101',
            'status': Course.STATUS_ACTIVE,
            'categories': [str(category.id)],
        },
        format='json',
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data.get('title') == 'New Course' or response.data.get('course_code') == 'NEW101'
    assert Course.objects.filter(course_code='NEW101').exists()


def test_course_destroy_as_instructor(api_client, create_user, create_course):
    """Instructor can soft-delete own active course with no enrollments."""
    instructor = create_user(
        email='di@example.com', username='di', role='instructor'
    )
    code = f'DEL{uuid.uuid4().hex[:6]}'
    course = create_course(
        course_code=code,
        instructor=instructor,
        is_active=True,
        status=Course.STATUS_ACTIVE,
    )
    api_client.force_authenticate(user=instructor)
    response = api_client.delete(f'/api/v1/courses/{course.id}/')
    assert response.status_code == status.HTTP_200_OK, response.data
    course.refresh_from_db()
    assert course.is_active is False


def test_course_destroy_already_deleted_returns_404(
    api_client, create_user, create_course
):
    """Inactive courses are filtered out of queryset, so delete returns 404."""
    instructor = create_user(
        email='di2@example.com', username='di2', role='instructor'
    )
    course = create_course(
        course_code=f'DEL2-{uuid.uuid4().hex[:6]}',
        instructor=instructor,
        is_active=False,
    )
    api_client.force_authenticate(user=instructor)
    response = api_client.delete(f'/api/v1/courses/{course.id}/')
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_course_destroy_in_progress_with_students_returns_400(
    api_client, create_user, create_course, create_enrollment
):
    """Cannot delete course in progress with enrolled students."""
    instructor = create_user(
        email='di3@example.com', username='di3', role='instructor'
    )
    course = create_course(
        course_code=f'DEL3-{uuid.uuid4().hex[:6]}',
        instructor=instructor,
        is_active=True,
        status=Course.STATUS_ACTIVE,
        max_students=2,
    )
    create_enrollment(course=course, is_active=True)
    create_enrollment(course=course, is_active=True)
    Course.objects.filter(pk=course.pk).update(status=Course.STATUS_IN_PROGRESS)
    course.refresh_from_db()
    api_client.force_authenticate(user=instructor)
    response = api_client.delete(f'/api/v1/courses/{course.id}/')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_course_enrolled_students_as_instructor(
    api_client, create_user, create_course, create_enrollment
):
    """Instructor can list enrolled students for own course (URL: enrolled-students)."""
    instructor = create_user(
        email='ei@example.com', username='ei', role='instructor'
    )
    course = create_course(
        course_code=f'ENR1-{uuid.uuid4().hex[:6]}',
        instructor=instructor,
        is_active=True,
    )
    create_enrollment(course=course, is_active=True)
    api_client.force_authenticate(user=instructor)
    response = api_client.get(f'/api/v1/courses/{course.id}/enrolled-students/')
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data
    assert response.data['count'] >= 1
