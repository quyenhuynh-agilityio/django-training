"""Tests for notification Celery tasks."""

import uuid
from unittest.mock import patch

import pytest

from core.choices import NotificationType
from notifications.models import Notification
from notifications.tasks import (
    create_student_enrolled_notification,
    create_student_removed_notification,
)

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
class TestCreateStudentEnrolledNotification:
    """Tests for create_student_enrolled_notification task."""

    @patch('notifications.tasks.sentry_scope')
    def test_creates_notification_for_instructor(
        self, mock_sentry_scope, create_user
    ):
        instructor = create_user(
            email='instructor@example.com', username='instructor', role='instructor'
        )
        student = create_user(
            email='student@example.com', username='student',
            first_name='Jane', last_name='Doe',
        )
        course_id = uuid.uuid4()

        result = create_student_enrolled_notification(
            instructor_id=instructor.id,
            student_id=student.id,
            student_name=student.full_name,
            student_email=student.email,
            course_id=course_id,
            course_code='CS101',
            course_title='Intro to CS',
        )

        assert result['status'] == 'success'
        assert 'notification_id' in result
        notification = Notification.objects.get(id=result['notification_id'])
        assert notification.recipient_id == instructor.id
        assert notification.type == NotificationType.STUDENT_ENROLLED
        assert notification.payload['student_email'] == student.email
        assert notification.payload['course_code'] == 'CS101'
        assert notification.payload['course_title'] == 'Intro to CS'
        assert 'has enrolled in' in notification.payload['message']

    @patch('notifications.tasks.cache')
    @patch('notifications.tasks.sentry_scope')
    def test_cache_delete_failure_does_not_fail_task(
        self, mock_sentry_scope, mock_cache, create_user
    ):
        """Task succeeds even when cache invalidation fails (best-effort)."""
        mock_cache.delete.side_effect = Exception('Redis down')
        instructor = create_user(email='instr@example.com', username='instr')
        student = create_user(email='stud@example.com', username='stud')

        result = create_student_enrolled_notification(
            instructor_id=instructor.id,
            student_id=student.id,
            student_name='Test User',
            student_email=student.email,
            course_id=uuid.uuid4(),
            course_code='CS101',
            course_title='Intro',
        )

        assert result['status'] == 'success'
        assert Notification.objects.filter(recipient_id=instructor.id).count() == 1

    @patch('notifications.tasks.sentry_capture_exception')
    @patch('notifications.tasks.sentry_scope')
    def test_captures_exception_on_create_failure(
        self, mock_sentry_scope, mock_sentry_capture, create_user
    ):
        """On create failure, task raises and captures exception in Sentry."""
        instructor = create_user(email='instr2@example.com', username='instr2')
        student = create_user(email='stud2@example.com', username='stud2')
        with patch.object(Notification.objects, 'create') as mock_create:
            mock_create.side_effect = Exception('DB error')

            with pytest.raises(Exception, match='DB error'):
                create_student_enrolled_notification(
                    instructor_id=instructor.id,
                    student_id=student.id,
                    student_name='Test',
                    student_email=student.email,
                    course_id=uuid.uuid4(),
                    course_code='CS101',
                    course_title='Intro',
                )

            mock_sentry_capture.assert_called_once()


@pytest.mark.django_db
class TestCreateStudentRemovedNotification:
    """Tests for create_student_removed_notification task."""

    @patch('notifications.tasks.sentry_scope')
    def test_creates_notification_for_student(self, mock_sentry_scope, create_user):
        student = create_user(email='student-removed@example.com', username='student_removed')
        course_id = uuid.uuid4()

        result = create_student_removed_notification(
            student_id=student.id,
            course_id=course_id,
            course_code='MATH201',
            course_title='Calculus',
        )

        assert result['status'] == 'success'
        notification = Notification.objects.get(id=result['notification_id'])
        assert notification.recipient_id == student.id
        assert notification.type == NotificationType.STUDENT_REMOVED
        assert notification.payload['course_code'] == 'MATH201'
        assert 'removed from' in notification.payload['message']
        assert notification.payload['removed_by_name'] == 'System'

    @patch('notifications.tasks.sentry_scope')
    def test_payload_includes_removed_by_when_provided(
        self, mock_sentry_scope, create_user
    ):
        student = create_user(email='student2@example.com', username='student2')
        remover = create_user(
            email='instructor@example.com', username='instructor',
            first_name='Dr', last_name='Smith',
        )

        result = create_student_removed_notification(
            student_id=student.id,
            course_id=uuid.uuid4(),
            course_code='PHY101',
            course_title='Physics',
            removed_by_id=remover.id,
            removed_by_name='Dr Smith',
        )

        notification = Notification.objects.get(id=result['notification_id'])
        assert notification.payload['removed_by_name'] == 'Dr Smith'
        assert 'by Dr Smith' in notification.payload['message']

    @patch('notifications.tasks.cache')
    @patch('notifications.tasks.sentry_scope')
    def test_cache_delete_failure_does_not_fail_task(
        self, mock_sentry_scope, mock_cache, create_user
    ):
        mock_cache.delete.side_effect = Exception('Cache error')
        student = create_user(email='student3@example.com', username='student3')

        result = create_student_removed_notification(
            student_id=student.id,
            course_id=uuid.uuid4(),
            course_code='CS101',
            course_title='Intro',
        )

        assert result['status'] == 'success'
        assert Notification.objects.filter(recipient_id=student.id).count() == 1
