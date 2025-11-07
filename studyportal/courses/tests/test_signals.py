# courses/tests/test_signals.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from courses.models import Course, Category
from enrollments.models import Enrollment

User = get_user_model()


class CourseSignalsTestCase(TestCase):
    """Test cases for course-related signals."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
        )
        self.category = Category.objects.create(name="Test Category", is_active=True)
        self.course = Course.objects.create(
            title="Test Course",
            course_code="TC101",
            description="Test Description",
            is_active=True,
        )
        self.course.categories.add(self.category)

    def test_course_deactivation_deactivates_enrollments(self):
        """Test that when a course is deactivated, its enrollments are deactivated."""
        # Create active enrollment
        enrollment = Enrollment.objects.create(
            user=self.user, course=self.course, is_active=True
        )
        self.assertTrue(enrollment.is_active)

        # Deactivate course
        self.course.is_active = False
        self.course.save()

        # Enrollment should be deactivated
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)

    def test_multiple_enrollments_deactivated_when_course_deactivated(self):
        """Test that all enrollments are deactivated when course is deactivated."""
        # Create multiple enrollments
        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="password123",
        )

        enrollment1 = Enrollment.objects.create(
            user=self.user, course=self.course, is_active=True
        )
        enrollment2 = Enrollment.objects.create(
            user=user2, course=self.course, is_active=True
        )

        # Deactivate course
        self.course.is_active = False
        self.course.save()

        # Both enrollments should be deactivated
        enrollment1.refresh_from_db()
        enrollment2.refresh_from_db()
        self.assertFalse(enrollment1.is_active)
        self.assertFalse(enrollment2.is_active)

    def test_only_active_enrollments_deactivated(self):
        """Test that only active enrollments are deactivated when course is deactivated."""
        # Create one active and one inactive enrollment
        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="password123",
        )

        enrollment1 = Enrollment.objects.create(
            user=self.user, course=self.course, is_active=True
        )
        enrollment2 = Enrollment.objects.create(
            user=user2, course=self.course, is_active=False
        )

        # Deactivate course
        self.course.is_active = False
        self.course.save()

        # Only active enrollment should be deactivated
        enrollment1.refresh_from_db()
        enrollment2.refresh_from_db()
        self.assertFalse(enrollment1.is_active)
        self.assertFalse(enrollment2.is_active)  # Already inactive, stays inactive

    def test_reactivate_course_does_not_reactivate_enrollments(self):
        """Test that reactivating course does not automatically reactivate enrollments."""
        enrollment = Enrollment.objects.create(
            user=self.user, course=self.course, is_active=True
        )

        # Deactivate course (enrollment becomes inactive)
        self.course.is_active = False
        self.course.save()
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)

        # Reactivate course
        self.course.is_active = True
        self.course.save()

        # Enrollment should remain inactive
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)
