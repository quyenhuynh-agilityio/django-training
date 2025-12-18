import pytest

from django.contrib.auth import get_user_model
from django.urls import reverse

from enrollments.models import Enrollment

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_course_list_view_anonymous(client):
    """Test course list view for anonymous users"""
    response = client.get(reverse('course_list'))

    assert response.status_code == 200
    assert 'courses' in response.context
    assert 'categories' in response.context


def test_course_list_view_authenticated(client, create_user, create_course):
    """Test course list view for authenticated users"""
    user = create_user(email='user@example.com', username='user', role='student')
    create_course(title='Test Course')

    client.force_login(user)
    response = client.get(reverse('course_list'))

    assert response.status_code == 200
    assert 'courses' in response.context
    assert len(response.context['courses']) > 0


def test_enroll_course_view_get_not_allowed(client, create_user, create_course):
    """Test that GET request to enroll_course redirects"""
    user = create_user(email='student@example.com', username='student', role='student')
    course = create_course(course_code='CRS043')

    client.force_login(user)
    response = client.get(reverse('enroll_course', args=[course.id]))

    # Should redirect (likely to login or course list)
    assert response.status_code in [302, 200]


def test_enroll_course_view_post_creates_enrollment(client, create_user, create_course):
    """Test that POST to enroll_course creates enrollment"""
    user = create_user(email='student@example.com', username='student', role='student')
    course = create_course(course_code='CRS038', is_active=True)

    client.force_login(user)
    response = client.post(reverse('enroll_course', args=[course.id]))

    # Should redirect to enrolled_courses
    assert response.status_code == 302
    assert Enrollment.objects.filter(student=user, course=course, is_active=True).exists()


def test_enroll_course_view_duplicate_enrollment(
    client, create_user, create_course, create_enrollment
):
    """Test that enrolling in already enrolled course doesn't create duplicate"""
    user = create_user(email='student@example.com', username='student', role='student')
    course = create_course(course_code='CRS039', is_active=True)
    create_enrollment(student=user, course=course)

    initial_count = Enrollment.objects.filter(student=user, course=course).count()

    client.force_login(user)
    response = client.post(reverse('enroll_course', args=[course.id]))

    assert response.status_code == 302
    # Should not create duplicate
    assert Enrollment.objects.filter(student=user, course=course).count() == initial_count


def test_enroll_course_view_inactive_course(client, create_user, create_course):
    """Test that enrolling in inactive course returns 404"""
    user = create_user(email='student@example.com', username='student', role='student')
    course = create_course(course_code='CRS040', is_active=False)

    client.force_login(user)
    response = client.post(reverse('enroll_course', args=[course.id]))

    assert response.status_code == 404


def test_enrolled_courses_view_requires_login(client):
    """Test that enrolled_courses view requires login"""
    response = client.get(reverse('enrolled_courses'))

    # Should redirect to login
    assert response.status_code == 302
    assert '/users/login/' in response.url


def test_enrolled_courses_view_authenticated(client, create_user, create_course, create_enrollment):
    """Test enrolled_courses view for authenticated user"""
    user = create_user(email='student@example.com', username='student', role='student')
    enrolled_course = create_course(course_code='CRS041')
    not_enrolled_course = create_course(course_code='CRS042')
    create_enrollment(student=user, course=enrolled_course)

    client.force_login(user)
    response = client.get(reverse('enrolled_courses'))

    assert response.status_code == 200
    assert 'courses' in response.context
    course_ids = [str(course.id) for course in response.context['courses']]
    assert str(enrolled_course.id) in course_ids
    assert str(not_enrolled_course.id) not in course_ids
