"""
Tests for Course-Related Celery Tasks

Tests cover:
- Course capacity email notifications
- Inactive course cleanup
- Monthly enrollment reports
"""

import csv
import io
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from django.utils import timezone

from core.choices import UserRole
from courses.models import Course
from courses.tasks import (
    cleanup_inactive_courses,
    send_course_full_email,
    send_monthly_enrollment_report,
)


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
class TestSendMonthlyEnrollmentReport:
    """Tests for send_monthly_enrollment_report task"""

    @patch('courses.tasks.EmailMessage')
    def test_sends_report_to_instructors(
        self, mock_email_class, create_user, create_course, create_enrollment
    ):
        """Test sends CSV report to each instructor"""
        # Mock EmailMessage instance
        mock_email = MagicMock()
        mock_email_class.return_value = mock_email

        # Create instructors with unique usernames
        instructor1 = create_user(
            email='instructor1@example.com',
            username=f'instructor1_{uuid.uuid4().hex[:6]}',
            role=UserRole.INSTRUCTOR,
        )
        instructor2 = create_user(
            email='instructor2@example.com',
            username=f'instructor2_{uuid.uuid4().hex[:6]}',
            role=UserRole.INSTRUCTOR,
        )

        # Create courses with unique codes
        course1 = create_course(
            course_code=f'RPT1{uuid.uuid4().hex[:6]}', instructor=instructor1, title='Course 1'
        )
        course2 = create_course(
            course_code=f'RPT2{uuid.uuid4().hex[:6]}', instructor=instructor2, title='Course 2'
        )

        # Create enrollments
        for _ in range(3):
            create_enrollment(course=course1, is_active=True)
        for _ in range(2):
            create_enrollment(course=course2, is_active=True)

        result = send_monthly_enrollment_report()

        # Check result
        assert result['status'] == 'success'
        assert result['reports_sent'] == 2

        # Check emails were created and sent
        assert mock_email_class.call_count == 2
        assert mock_email.send.call_count == 2

    @patch('courses.tasks.EmailMessage')
    def test_csv_contains_correct_data(self, mock_email_class, create_course, create_enrollment):
        """Test CSV file contains correct enrollment data"""
        mock_email = MagicMock()
        mock_email_class.return_value = mock_email

        course = create_course(course_code=f'CSV{uuid.uuid4().hex[:6]}', title='Test Course')

        # Create 5 active enrollments
        for _ in range(5):
            create_enrollment(course=course, is_active=True)

        send_monthly_enrollment_report('January 2026')

        # Get CSV content from attach call
        attach_call = mock_email.attach.call_args
        csv_content = attach_call[0][1]

        # Parse CSV
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)

        # Check headers
        assert rows[0] == ['Course ID', 'Course Code', 'Course Title', 'Active Enrollments']

        # Check data row
        assert len(rows) == 2  # Header + 1 course
        assert rows[1][1] == course.course_code
        assert rows[1][2] == 'Test Course'
        assert rows[1][3] == '5'

    def test_handles_no_courses(self):
        """Test handles case with no courses"""
        result = send_monthly_enrollment_report()

        assert result['status'] == 'no_courses'

    @patch('courses.tasks._send_instructor_monthly_report')
    def test_continues_on_single_instructor_failure(self, mock_send_report, create_course):
        """Test continues sending to other instructors if one fails"""
        # First instructor succeeds, second fails
        mock_send_report.side_effect = [None, Exception('SMTP error'), None]

        # Create 3 courses with different instructors and unique codes
        for i in range(3):
            create_course(course_code=f'FAIL{i}{uuid.uuid4().hex[:6]}')

        result = send_monthly_enrollment_report()

        # Should still report success for the ones that worked
        assert result['status'] == 'success'


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
