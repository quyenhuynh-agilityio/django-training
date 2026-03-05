"""
Tests for Course-Related Celery Tasks

Tests cover:
- Course capacity email notifications
- Inactive course cleanup
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest

from django.utils import timezone

from courses.models import Course
from courses.tasks import cleanup_inactive_courses, send_course_full_email


@pytest.mark.django_db
class TestSendCourseFullEmail:
    """Tests for send_course_full_email task"""

    @patch('courses.tasks.send_mail')
    def test_sends_email_when_course_full(self, mock_send_mail, create_course, create_enrollment):
        """Test email is sent when course reaches capacity"""
        course = create_course(course_code=f'FULL{uuid.uuid4().hex[:6]}', max_students=3)

        # Fill the course
        for _ in range(3):
            create_enrollment(course=course, is_active=True)

        send_course_full_email(course.id)

        assert mock_send_mail.called
        call_kwargs = mock_send_mail.call_args[1]

        assert course.instructor.email in call_kwargs['recipient_list']
        assert course.title in call_kwargs['html_message']

    @patch('courses.tasks.send_mail')
    def test_skips_email_when_course_not_full(
        self, mock_send_mail, create_course, create_enrollment
    ):
        """Test email is not sent if course is no longer full"""
        course = create_course(course_code=f'NOTFULL{uuid.uuid4().hex[:6]}', max_students=5)

        # Only 2 enrollments
        for _ in range(2):
            create_enrollment(course=course, is_active=True)

        send_course_full_email(course.id)

        # Email should not be sent
        assert not mock_send_mail.called

    @patch('courses.tasks.send_mail')
    def test_handles_missing_instructor_email(
        self, mock_send_mail, create_course, create_enrollment
    ):
        """Test handles course without instructor email gracefully"""
        course = create_course(course_code=f'NOEMAIL{uuid.uuid4().hex[:6]}', max_students=1)

        # Make course full first
        create_enrollment(course=course, is_active=True)

        # Now remove instructor email
        course.instructor.email = ''
        course.instructor.save()

        # Task should handle missing email gracefully without crashing
        try:
            send_course_full_email(course.id)
        except Exception as e:
            pytest.fail(f'Task should not raise exception, but raised: {e}')

        # Email should not be sent when email is missing
        assert not mock_send_mail.called


@pytest.mark.django_db
class TestCleanupInactiveCourses:
    """Tests for cleanup_inactive_courses task"""

    def test_deletes_old_inactive_courses(self, create_course):
        """Test deletes courses inactive for 3+ months"""
        # Create old inactive course
        old_course = create_course(course_code=f'OLD{uuid.uuid4().hex[:6]}', is_active=False)
        # Manually update the timestamp to avoid auto_now
        Course.objects.filter(id=old_course.id).update(
            updated_at=timezone.now() - timedelta(days=91)
        )
        old_course.refresh_from_db()

        # Create recent inactive course
        recent_course = create_course(course_code=f'RECENT{uuid.uuid4().hex[:6]}', is_active=False)
        Course.objects.filter(id=recent_course.id).update(
            updated_at=timezone.now() - timedelta(days=30)
        )

        # Create active course
        active_course = create_course(course_code=f'ACTIVE{uuid.uuid4().hex[:6]}', is_active=True)

        result = cleanup_inactive_courses()

        # Check only old inactive course deleted
        assert result['deleted_count'] == 1
        assert not Course.objects.filter(id=old_course.id).exists()
        assert Course.objects.filter(id=recent_course.id).exists()
        assert Course.objects.filter(id=active_course.id).exists()

    def test_returns_zero_when_no_courses_to_delete(self, create_course):
        """Test returns 0 when no courses need cleanup"""
        # All courses are active or recent
        for i in range(3):
            create_course(course_code=f'KEEP{i}{uuid.uuid4().hex[:6]}', is_active=True)

        result = cleanup_inactive_courses()

        assert result['deleted_count'] == 0


@pytest.mark.django_db
class TestCourseCapacityWorkflow:
    """Integration tests for course capacity notifications"""

    @patch('courses.tasks.send_mail')
    def test_instructor_notified_when_course_full(
        self, mock_send_mail, create_course, create_enrollment
    ):
        """Test instructor receives notification when course reaches capacity"""

        course = create_course(course_code=f'NOTIFY{uuid.uuid4().hex[:6]}', max_students=2)

        # Enroll students up to capacity
        create_enrollment(course=course, is_active=True)
        create_enrollment(course=course, is_active=True)

        # Trigger notification
        send_course_full_email(course.id)

        # Verify email sent
        assert mock_send_mail.called
