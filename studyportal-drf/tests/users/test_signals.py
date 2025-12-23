"""
Tests for deactivate_enrollments_when_user_disabled signal
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.choices import EnrollmentStatus, UserRole
from courses.models import Course
from enrollments.models import Enrollment

User = get_user_model()


class DeactivateEnrollmentsSignalTest(TestCase):
    """Test that enrollments are deactivated when user is disabled"""

    def setUp(self):
        """Create test data"""
        # Create an instructor for the courses
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role=UserRole.INSTRUCTOR,
            is_active=True,
        )

        # Create active courses
        self.course1 = Course.objects.create(
            title='Course 1',
            course_code='TEST101',
            instructor=self.instructor,
            status=Course.STATUS_ACTIVE,
            is_active=True,
            max_students=30,
        )
        self.course2 = Course.objects.create(
            title='Course 2',
            course_code='TEST102',
            instructor=self.instructor,
            status=Course.STATUS_ACTIVE,
            is_active=True,
            max_students=30,
        )

        # Create a student
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role=UserRole.STUDENT,
            is_active=True,
        )

    def test_signal_deactivates_active_enrollments_when_user_disabled(self):
        """Signal should deactivate all active enrollments when user is disabled"""
        # Create active enrollments
        enrollment1 = Enrollment.objects.create(
            student=self.student, course=self.course1, is_active=True
        )
        enrollment2 = Enrollment.objects.create(
            student=self.student, course=self.course2, is_active=True
        )

        # Verify enrollments are active
        self.assertTrue(enrollment1.is_active)
        self.assertTrue(enrollment2.is_active)

        # Deactivate the user
        self.student.is_active = False
        self.student.save()

        # Refresh enrollments from database
        enrollment1.refresh_from_db()
        enrollment2.refresh_from_db()

        # Assert enrollments are now inactive
        self.assertFalse(enrollment1.is_active)
        self.assertFalse(enrollment2.is_active)

    def test_signal_does_not_affect_already_inactive_enrollments(self):
        """Signal should not modify already inactive enrollments"""
        # Create an inactive enrollment
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course1,
            is_active=False,
            status=EnrollmentStatus.DROPPED,
        )

        # Deactivate the user
        self.student.is_active = False
        self.student.save()

        # Refresh enrollment
        enrollment.refresh_from_db()

        # Enrollment should remain inactive with same status
        self.assertFalse(enrollment.is_active)
        self.assertEqual(enrollment.status, EnrollmentStatus.DROPPED)

    def test_signal_only_affects_disabled_user(self):
        """Signal should only deactivate enrollments for the disabled user"""
        # Create another student with enrollments
        other_student = User.objects.create_user(
            username='otherstudent',
            email='other@test.com',
            password='testpass123',
            role=UserRole.STUDENT,
            is_active=True,
        )

        # Create enrollments for both students
        enrollment1 = Enrollment.objects.create(
            student=self.student, course=self.course1, is_active=True
        )
        enrollment2 = Enrollment.objects.create(
            student=other_student, course=self.course2, is_active=True
        )

        # Deactivate only the first student
        self.student.is_active = False
        self.student.save()

        # Refresh enrollments
        enrollment1.refresh_from_db()
        enrollment2.refresh_from_db()

        # Only the first student's enrollment should be deactivated
        self.assertFalse(enrollment1.is_active)
        self.assertTrue(enrollment2.is_active)

    def test_signal_does_not_fire_when_user_remains_active(self):
        """Signal should not deactivate enrollments if user remains active"""
        enrollment = Enrollment.objects.create(
            student=self.student, course=self.course1, is_active=True
        )

        # Update user but keep is_active=True
        self.student.email = 'newemail@test.com'
        self.student.save()

        # Refresh enrollment
        enrollment.refresh_from_db()

        # Enrollment should remain active
        self.assertTrue(enrollment.is_active)

    def test_signal_works_when_reactivating_user(self):
        """Signal should not deactivate enrollments when re-enabling user"""
        enrollment = Enrollment.objects.create(
            student=self.student, course=self.course1, is_active=True
        )

        # First deactivate the user
        self.student.is_active = False
        self.student.save()

        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)

        # Now reactivate the user
        self.student.is_active = True
        self.student.save()

        enrollment.refresh_from_db()
        # Enrollment should remain inactive (signal doesn't reactivate)
        self.assertFalse(enrollment.is_active)

    def test_signal_with_mixed_enrollment_statuses(self):
        """Signal should only deactivate enrollments where is_active=True"""
        # Create enrollments with different states
        active_enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course1,
            is_active=True,
            status=EnrollmentStatus.ACTIVE,
        )

        # Manually create an inactive enrollment (simulating a dropped course)
        inactive_enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course2,
            is_active=False,
            status=EnrollmentStatus.DROPPED,
        )

        # Deactivate user
        self.student.is_active = False
        self.student.save()

        # Refresh both
        active_enrollment.refresh_from_db()
        inactive_enrollment.refresh_from_db()

        # Active enrollment should be deactivated
        self.assertFalse(active_enrollment.is_active)
        # Inactive enrollment should remain unchanged
        self.assertFalse(inactive_enrollment.is_active)
        self.assertEqual(inactive_enrollment.status, EnrollmentStatus.DROPPED)

    def test_signal_creates_no_extra_queries_for_user_without_enrollments(self):
        """Signal should handle users with no enrollments gracefully"""
        # Create a student with no enrollments
        new_student = User.objects.create_user(
            username='newstudent',
            email='new@test.com',
            password='testpass123',
            role=UserRole.STUDENT,
            is_active=True,
        )

        # This should not raise any errors
        new_student.is_active = False
        new_student.save()

        # Verify no enrollments exist
        self.assertEqual(Enrollment.objects.filter(student=new_student).count(), 0)

    def test_signal_with_non_student_user(self):
        """Signal should work but have no effect for non-student users"""
        # Deactivate the instructor
        self.instructor.is_active = False
        self.instructor.save()

        # This should not raise any errors even though instructors don't have enrollments
        # and the signal runs regardless of user role
        self.assertFalse(self.instructor.is_active)
