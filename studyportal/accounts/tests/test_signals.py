# accounts/tests/test_signals.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from enrollments.models import Enrollment
from courses.models import Course, Category

User = get_user_model()


class UserSignalsTestCase(TestCase):
    """Test cases for user-related signals."""

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

    def test_deactivate_enrollments_when_user_inactive(self):
        """Test that enrollments are deactivated when user is deactivated."""
        # Create active enrollment
        enrollment = Enrollment.objects.create(
            user=self.user, course=self.course, is_active=True
        )
        self.assertTrue(enrollment.is_active)

        # Deactivate user
        self.user.is_active = False
        self.user.save()

        # Enrollment should be deactivated
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)

    def test_multiple_enrollments_deactivated(self):
        """Test that all user enrollments are deactivated when user is deactivated."""
        # Create multiple enrollments
        course2 = Course.objects.create(
            title="Test Course 2",
            course_code="TC102",
            description="Test Description 2",
            is_active=True,
        )
        course2.categories.add(self.category)

        enrollment1 = Enrollment.objects.create(
            user=self.user, course=self.course, is_active=True
        )
        enrollment2 = Enrollment.objects.create(
            user=self.user, course=course2, is_active=True
        )

        # Deactivate user
        self.user.is_active = False
        self.user.save()

        # Both enrollments should be deactivated
        enrollment1.refresh_from_db()
        enrollment2.refresh_from_db()
        self.assertFalse(enrollment1.is_active)
        self.assertFalse(enrollment2.is_active)

    def test_only_active_enrollments_deactivated(self):
        """Test that only active enrollments are deactivated."""
        # Create one active and one inactive enrollment
        enrollment1 = Enrollment.objects.create(
            user=self.user, course=self.course, is_active=True
        )
        course2 = Course.objects.create(
            title="Test Course 2",
            course_code="TC102",
            description="Test Description 2",
            is_active=True,
        )
        course2.categories.add(self.category)
        enrollment2 = Enrollment.objects.create(
            user=self.user, course=course2, is_active=False
        )

        # Deactivate user
        self.user.is_active = False
        self.user.save()

        # Only active enrollment should be deactivated
        enrollment1.refresh_from_db()
        enrollment2.refresh_from_db()
        self.assertFalse(enrollment1.is_active)
        self.assertFalse(enrollment2.is_active)  # Already inactive, stays inactive

    def test_reactivate_user_does_not_reactivate_enrollments(self):
        """Test that reactivating user does not automatically reactivate enrollments."""
        enrollment = Enrollment.objects.create(
            user=self.user, course=self.course, is_active=True
        )

        # Deactivate user (enrollment becomes inactive)
        self.user.is_active = False
        self.user.save()
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)

        # Reactivate user
        self.user.is_active = True
        self.user.save()

        # Enrollment should remain inactive
        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)
