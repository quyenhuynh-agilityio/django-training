"""
Tests for Reports-Related Celery Tasks

Currently covers:
- Monthly enrollment reports
"""

import csv
import io
import uuid
from unittest.mock import MagicMock, patch

import pytest

from core.choices import UserRole
from reports.tasks import send_monthly_enrollment_report


@pytest.mark.django_db
class TestSendMonthlyEnrollmentReport:
    """Tests for send_monthly_enrollment_report task"""

    @patch('reports.tasks.EmailMessage')
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

    @patch('reports.tasks.EmailMessage')
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

    @patch('reports.tasks._send_instructor_monthly_report')
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

