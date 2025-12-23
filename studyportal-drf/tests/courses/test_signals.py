"""
Tests for deactivate_enrollments_when_course_disabled signal
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.choices import CourseStatus, EnrollmentStatus, UserRole
from courses.models import Course
from enrollments.models import Enrollment

User = get_user_model()


class DeactivateEnrollmentsWhenCourseDisabledSignalTest(TestCase):
    """Test that enrollments are deactivated when course is disabled"""

    def setUp(self):
        """Create test data"""
        # Create an instructor
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role=UserRole.INSTRUCTOR,
            is_active=True,
        )

        # Create students
        self.student1 = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='testpass123',
            role=UserRole.STUDENT,
            is_active=True,
        )
        self.student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='testpass123',
            role=UserRole.STUDENT,
            is_active=True,
        )
        self.student3 = User.objects.create_user(
            username='student3',
            email='student3@test.com',
            password='testpass123',
            role=UserRole.STUDENT,
            is_active=True,
        )

        # Create an active course
        self.course = Course.objects.create(
            title='Test Course',
            course_code='TEST101',
            instructor=self.instructor,
            status=CourseStatus.ACTIVE,
            is_active=True,
            max_students=30,
        )

    def test_signal_deactivates_all_active_enrollments_when_course_disabled(self):
        """Signal should deactivate all active enrollments when course is disabled"""
        # Create multiple active enrollments
        enrollment1 = Enrollment.objects.create(
            student=self.student1, course=self.course, is_active=True
        )
        enrollment2 = Enrollment.objects.create(
            student=self.student2, course=self.course, is_active=True
        )
        enrollment3 = Enrollment.objects.create(
            student=self.student3, course=self.course, is_active=True
        )

        # Verify all enrollments are active
        self.assertTrue(enrollment1.is_active)
        self.assertTrue(enrollment2.is_active)
        self.assertTrue(enrollment3.is_active)

        # Deactivate the course
        self.course.is_active = False
        self.course.save()

        # Refresh enrollments from database
        enrollment1.refresh_from_db()
        enrollment2.refresh_from_db()
        enrollment3.refresh_from_db()

        # Assert all enrollments are now inactive
        self.assertFalse(enrollment1.is_active)
        self.assertFalse(enrollment2.is_active)
        self.assertFalse(enrollment3.is_active)

    def test_signal_does_not_affect_already_inactive_enrollments(self):
        """Signal should not modify already inactive enrollments"""
        # Create an inactive enrollment
        enrollment = Enrollment.objects.create(
            student=self.student1,
            course=self.course,
            is_active=False,
            status=EnrollmentStatus.DROPPED,
        )

        # Deactivate the course
        self.course.is_active = False
        self.course.save()

        # Refresh enrollment
        enrollment.refresh_from_db()

        # Enrollment should remain inactive with same status
        self.assertFalse(enrollment.is_active)
        self.assertEqual(enrollment.status, EnrollmentStatus.DROPPED)

    def test_signal_only_affects_disabled_course(self):
        """Signal should only deactivate enrollments for the disabled course"""
        # Create another course
        other_course = Course.objects.create(
            title='Other Course',
            course_code='OTHER202',
            instructor=self.instructor,
            status=CourseStatus.ACTIVE,
            is_active=True,
            max_students=30,
        )

        # Create enrollments for both courses
        enrollment1 = Enrollment.objects.create(
            student=self.student1, course=self.course, is_active=True
        )
        enrollment2 = Enrollment.objects.create(
            student=self.student2, course=other_course, is_active=True
        )

        # Deactivate only the first course
        self.course.is_active = False
        self.course.save()

        # Refresh enrollments
        enrollment1.refresh_from_db()
        enrollment2.refresh_from_db()

        # Only the first course's enrollment should be deactivated
        self.assertFalse(enrollment1.is_active)
        self.assertTrue(enrollment2.is_active)

    def test_signal_does_not_fire_when_course_remains_active(self):
        """Signal should not deactivate enrollments if course remains active"""
        enrollment = Enrollment.objects.create(
            student=self.student1, course=self.course, is_active=True
        )

        # Update course but keep is_active=True
        self.course.title = 'Updated Title'
        self.course.save()

        # Refresh enrollment
        enrollment.refresh_from_db()

        # Enrollment should remain active
        self.assertTrue(enrollment.is_active)

    def test_signal_with_course_status_change_while_active(self):
        """Signal should not deactivate enrollments when only status changes"""
        enrollment = Enrollment.objects.create(
            student=self.student1, course=self.course, is_active=True
        )

        # Change course status but keep is_active=True
        self.course.status = CourseStatus.IN_PROGRESS
        self.course.save()

        enrollment.refresh_from_db()

        # Enrollment should remain active
        self.assertTrue(enrollment.is_active)

    def test_signal_with_mixed_enrollment_statuses(self):
        """Signal should only deactivate enrollments where is_active=True"""
        # Create enrollments with different states
        active_enrollment = Enrollment.objects.create(
            student=self.student1,
            course=self.course,
            is_active=True,
            status=EnrollmentStatus.ACTIVE,
        )

        completed_enrollment = Enrollment.objects.create(
            student=self.student2,
            course=self.course,
            is_active=True,
            status=EnrollmentStatus.COMPLETED,
        )

        dropped_enrollment = Enrollment.objects.create(
            student=self.student3,
            course=self.course,
            is_active=False,
            status=EnrollmentStatus.DROPPED,
        )

        # Deactivate course
        self.course.is_active = False
        self.course.save()

        # Refresh all
        active_enrollment.refresh_from_db()
        completed_enrollment.refresh_from_db()
        dropped_enrollment.refresh_from_db()

        # Active enrollments should be deactivated
        self.assertFalse(active_enrollment.is_active)
        self.assertFalse(completed_enrollment.is_active)
        # Already inactive enrollment should remain unchanged
        self.assertFalse(dropped_enrollment.is_active)
        self.assertEqual(dropped_enrollment.status, EnrollmentStatus.DROPPED)

    def test_signal_with_course_without_enrollments(self):
        """Signal should handle courses with no enrollments gracefully"""
        # Create a course with no enrollments
        empty_course = Course.objects.create(
            title='Empty Course',
            course_code='EMPTY303',
            instructor=self.instructor,
            status=CourseStatus.ACTIVE,
            is_active=True,
            max_students=30,
        )

        # This should not raise any errors
        empty_course.is_active = False
        empty_course.save()

        # Verify no enrollments exist
        self.assertEqual(Enrollment.objects.filter(course=empty_course).count(), 0)

    def test_signal_with_soft_delete_method(self):
        """Signal should work when using the soft_delete() method"""
        enrollment = Enrollment.objects.create(
            student=self.student1, course=self.course, is_active=True
        )

        # Use the soft_delete method instead of directly setting is_active
        self.course.soft_delete()

        # Refresh enrollment
        enrollment.refresh_from_db()

        # Enrollment should be deactivated
        self.assertFalse(enrollment.is_active)
        self.assertFalse(self.course.is_active)

    def test_signal_when_reactivating_course(self):
        """Signal should not reactivate enrollments when course is reactivated"""
        enrollment = Enrollment.objects.create(
            student=self.student1, course=self.course, is_active=True
        )

        # First deactivate the course
        self.course.is_active = False
        self.course.save()

        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)

        # Now reactivate the course
        self.course.is_active = True
        self.course.save()

        enrollment.refresh_from_db()
        # Enrollment should remain inactive (signal doesn't reactivate)
        self.assertFalse(enrollment.is_active)

    def test_signal_with_draft_course_being_disabled(self):
        """Signal should work even for draft courses"""
        # Create course as ACTIVE first to allow enrollment
        draft_course = Course.objects.create(
            title='Draft Course',
            course_code='DRAFT404',
            instructor=self.instructor,
            status=CourseStatus.ACTIVE,  # Start as ACTIVE
            is_active=True,
            max_students=30,
        )

        # Create enrollment while course is ACTIVE
        enrollment = Enrollment.objects.create(
            student=self.student1, course=draft_course, is_active=True
        )

        # Now change course to DRAFT (using update to skip validation)
        Course.objects.filter(pk=draft_course.pk).update(status=CourseStatus.DRAFT)
        draft_course.refresh_from_db()

        # Verify enrollment exists and course is now DRAFT
        self.assertTrue(enrollment.is_active)
        self.assertEqual(draft_course.status, CourseStatus.DRAFT)

        # Deactivate the draft course
        draft_course.is_active = False
        draft_course.save()

        enrollment.refresh_from_db()

        # Enrollment should be deactivated
        self.assertFalse(enrollment.is_active)

    def test_signal_with_bulk_update(self):
        """Signal should fire for each course in a bulk update scenario"""
        # Create another course
        course2 = Course.objects.create(
            title='Course 2',
            course_code='TEST202',
            instructor=self.instructor,
            status=CourseStatus.ACTIVE,
            is_active=True,
            max_students=30,
        )

        # Create enrollments for both courses
        enrollment1 = Enrollment.objects.create(
            student=self.student1, course=self.course, is_active=True
        )
        enrollment2 = Enrollment.objects.create(
            student=self.student2, course=course2, is_active=True
        )

        # Note: bulk_update does NOT trigger signals
        # This test documents that limitation
        Course.objects.filter(pk__in=[self.course.pk, course2.pk]).update(is_active=False)

        enrollment1.refresh_from_db()
        enrollment2.refresh_from_db()

        # Enrollments will remain active because bulk update bypasses signals
        # This is expected Django behavior
        self.assertTrue(enrollment1.is_active)
        self.assertTrue(enrollment2.is_active)

        # But individual saves DO trigger the signal
        self.course.refresh_from_db()
        self.course.save()  # This will trigger the signal

        enrollment1.refresh_from_db()
        self.assertFalse(enrollment1.is_active)

    def test_signal_preserves_enrollment_status_field(self):
        """Signal should only update is_active, not the status field"""
        enrollment = Enrollment.objects.create(
            student=self.student1,
            course=self.course,
            is_active=True,
            status=EnrollmentStatus.COMPLETED,
        )

        # Deactivate course
        self.course.is_active = False
        self.course.save()

        enrollment.refresh_from_db()

        # is_active should be False but status should remain unchanged
        self.assertFalse(enrollment.is_active)
        self.assertEqual(enrollment.status, EnrollmentStatus.COMPLETED)
