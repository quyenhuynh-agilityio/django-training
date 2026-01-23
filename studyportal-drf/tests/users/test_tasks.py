"""
Tests for User-Related Celery Tasks

Tests cover:
- Email verification
- Welcome email
- Auto-enrollment in introduction courses
- Password reset emails
"""

from unittest.mock import patch

import pytest

from core.choices import UserRole
from courses.models import Course
from enrollments.models import Enrollment
from users.models import User
from users.tasks import (
    auto_enroll_intro_courses,
    send_password_reset_confirmation_email,
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)


@pytest.mark.django_db
class TestSendVerificationEmail:
    """Tests for send_verification_email task"""

    @patch('users.tasks.send_mail')
    def test_sends_verification_email_successfully(self, mock_send_mail, create_user):
        """Test verification email is sent with correct parameters"""

        user = create_user(email='test@example.com')
        token = 'test-token-123'

        send_verification_email(str(user.id), token)

        # Assert send_mail was called
        assert mock_send_mail.called
        call_kwargs = mock_send_mail.call_args[1]

        # Check email details
        assert 'Verify' in call_kwargs['subject']
        assert user.email in call_kwargs['recipient_list']
        assert token in call_kwargs['html_message']

    @patch('users.tasks.send_mail')
    def test_handles_nonexistent_user(self, mock_send_mail):
        """Test task handles nonexistent user gracefully"""

        fake_user_id = '00000000-0000-0000-0000-000000000000'

        with pytest.raises(User.DoesNotExist):
            send_verification_email(fake_user_id, 'token')

        # Email should not be sent
        assert not mock_send_mail.called

    @patch('users.tasks.send_mail')
    @patch('users.tasks.sentry_sdk')
    def test_captures_exception_in_sentry(self, mock_sentry, mock_send_mail, create_user):
        """Test exceptions are captured in Sentry"""

        user = create_user()
        mock_send_mail.side_effect = Exception('SMTP error')

        with pytest.raises(Exception):  # noqa: B017
            send_verification_email(str(user.id), 'token')

        # Verify Sentry captured the exception
        mock_sentry.capture_exception.assert_called_once()


@pytest.mark.django_db
class TestSendWelcomeEmail:
    """Tests for send_welcome_email task"""

    @patch('users.tasks.send_mail')
    def test_sends_welcome_email_successfully(self, mock_send_mail, create_user):
        """Test welcome email is sent"""

        user = create_user(email='newuser@example.com')

        send_welcome_email(str(user.id))

        assert mock_send_mail.called
        call_kwargs = mock_send_mail.call_args[1]

        assert 'Welcome' in call_kwargs['subject']
        assert user.email in call_kwargs['recipient_list']

    @patch('users.tasks.send_mail')
    def test_includes_dashboard_url(self, mock_send_mail, create_user, settings):
        """Test welcome email includes dashboard URL"""

        settings.FRONTEND_URL = 'https://example.com'
        user = create_user()

        send_welcome_email(str(user.id))

        call_kwargs = mock_send_mail.call_args[1]
        assert 'example.com/dashboard' in call_kwargs['html_message']


@pytest.mark.django_db
class TestAutoEnrollIntroCourses:
    """Tests for auto_enroll_intro_courses task"""

    def test_enrolls_user_in_introduction_courses(self, create_user, create_course, settings):
        """Test user is auto-enrolled in introduction courses"""

        settings.AUTO_ENROLL_INTRO_COURSES = True

        user = create_user(role=UserRole.STUDENT)

        # Create intro courses with unique course codes
        intro_course1 = create_course(
            course_code='INTRO101',
            is_introduction=True,
            is_active=True,
            status=Course.STATUS_ACTIVE,
        )
        intro_course2 = create_course(
            course_code='INTRO102',
            is_introduction=True,
            is_active=True,
            status=Course.STATUS_ACTIVE,
        )
        # Regular course - should not enroll
        create_course(course_code='REG101', is_introduction=False, is_active=True)

        auto_enroll_intro_courses(str(user.id))

        # Check enrollments created
        enrollments = Enrollment.objects.filter(student=user, is_active=True)
        assert enrollments.count() == 2
        assert set(enrollments.values_list('course_id', flat=True)) == {
            intro_course1.id,
            intro_course2.id,
        }

    def test_skips_enrollment_when_disabled(self, create_user, create_course, settings):
        """Test auto-enrollment is skipped when feature is disabled"""

        settings.AUTO_ENROLL_INTRO_COURSES = False

        user = create_user(role=UserRole.STUDENT)
        create_course(
            course_code='INTRO201',
            is_introduction=True,
            is_active=True,
            status=Course.STATUS_ACTIVE,
        )

        auto_enroll_intro_courses(str(user.id))

        # No enrollments should be created
        assert Enrollment.objects.filter(student=user).count() == 0

    def test_skips_full_courses(self, create_user, create_course, create_enrollment):
        """Test auto-enrollment skips courses at capacity"""

        user = create_user(role=UserRole.STUDENT)
        full_course = create_course(
            course_code='INTRO301',
            is_introduction=True,
            is_active=True,
            status=Course.STATUS_ACTIVE,
            max_students=2,
        )

        # Fill the course
        for _ in range(2):
            create_enrollment(course=full_course, is_active=True)

        auto_enroll_intro_courses(str(user.id))

        # User should not be enrolled
        assert not Enrollment.objects.filter(student=user, course=full_course).exists()

    def test_skips_already_enrolled_courses(self, create_user, create_course, create_enrollment):
        """Test auto-enrollment skips courses user is already enrolled in"""

        user = create_user(role=UserRole.STUDENT)
        intro_course = create_course(
            course_code='INTRO401',
            is_introduction=True,
            is_active=True,
            status=Course.STATUS_ACTIVE,
        )

        # User already enrolled
        create_enrollment(student=user, course=intro_course, is_active=True)

        initial_count = Enrollment.objects.filter(student=user).count()

        auto_enroll_intro_courses(str(user.id))

        # No new enrollments
        assert Enrollment.objects.filter(student=user).count() == initial_count

    def test_skips_inactive_courses(self, create_user, create_course):
        """Test auto-enrollment skips inactive courses"""

        user = create_user(role=UserRole.STUDENT)

        # Create course with is_active=False
        create_course(
            course_code='INTRO501',
            is_introduction=True,
            is_active=False,
            status=Course.STATUS_ACTIVE,  # Use valid status
        )

        # Create course with draft status (not active)
        create_course(
            course_code='INTRO502',
            is_introduction=True,
            is_active=True,
            status='draft',  # Draft courses should not auto-enroll
        )

        auto_enroll_intro_courses(str(user.id))

        # No enrollments - both courses should be skipped
        assert Enrollment.objects.filter(student=user).count() == 0


@pytest.mark.django_db
class TestSendPasswordResetEmail:
    """Tests for password reset email tasks"""

    @patch('users.tasks.send_mail')
    def test_sends_password_reset_email(self, mock_send_mail, create_user):
        """Test password reset email is sent"""

        user = create_user(email='user@example.com')
        reset_url = 'https://example.com/reset/token123'

        send_password_reset_email(str(user.id), reset_url)

        assert mock_send_mail.called
        call_kwargs = mock_send_mail.call_args[1]

        assert 'Password Reset' in call_kwargs['subject']
        assert user.email in call_kwargs['recipient_list']
        assert reset_url in call_kwargs['html_message']

    @patch('users.tasks.send_mail')
    def test_sends_password_reset_confirmation(self, mock_send_mail, create_user):
        """Test password reset confirmation email is sent"""

        user = create_user()

        send_password_reset_confirmation_email(str(user.id))

        assert mock_send_mail.called
        call_kwargs = mock_send_mail.call_args[1]

        assert 'Password' in call_kwargs['subject']
        assert user.email in call_kwargs['recipient_list']
