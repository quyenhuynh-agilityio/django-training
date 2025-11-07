# enrollments/tests/test_models.py
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from courses.models import Course, Category
from enrollments.models import Enrollment

User = get_user_model()


class EnrollmentModelTest(TestCase):
    """Test cases for Enrollment model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="password123",
        )
        self.category = Category.objects.create(name="Web Development", is_active=True)
        self.course = Course.objects.create(
            title="Django Basics",
            course_code="DJ101",
            description="Learn Django",
            is_active=True,
        )
        self.course.categories.add(self.category)

    def test_enrollment_creation(self):
        """Test creating an enrollment."""
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)

        self.assertEqual(enrollment.user.username, "student1")
        self.assertEqual(enrollment.course.title, "Django Basics")
        self.assertTrue(enrollment.is_active)  # default is True
        self.assertIsInstance(enrollment.id, uuid.UUID)
        self.assertIsNotNone(enrollment.enrolled_at)

    def test_enrollment_uuid_primary_key(self):
        """Test that enrollment ID is a UUID."""
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        self.assertIsInstance(enrollment.id, uuid.UUID)
        self.assertIsNotNone(enrollment.id)

    def test_enrollment_soft_delete(self):
        """Test soft deleting an enrollment."""
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        self.assertTrue(enrollment.is_active)

        enrollment.is_active = False
        enrollment.save()

        enrollment.refresh_from_db()
        self.assertFalse(enrollment.is_active)

    def test_enrollment_soft_delete_preserves_record(self):
        """Test that soft delete doesn't remove enrollment from database."""
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        enrollment_id = enrollment.id
        enrollment.is_active = False
        enrollment.save()

        # Enrollment should still exist in database
        self.assertTrue(Enrollment.objects.filter(id=enrollment_id).exists())
        retrieved_enrollment = Enrollment.objects.get(id=enrollment_id)
        self.assertFalse(retrieved_enrollment.is_active)

    def test_enrollment_string_representation(self):
        """Test enrollment __str__ method."""
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        expected = f"{self.user.username}  and {self.course.title}"
        self.assertEqual(str(enrollment), expected)

    def test_enrollment_unique_together_constraint(self):
        """Test that user and course combination must be unique."""
        Enrollment.objects.create(user=self.user, course=self.course)

        # Attempting to create duplicate enrollment should raise IntegrityError
        with self.assertRaises(IntegrityError):
            Enrollment.objects.create(user=self.user, course=self.course)

    def test_enrollment_ordering_by_enrolled_at_descending(self):
        """Test that enrollments are ordered by enrolled_at descending."""
        programming_category = Category.objects.create(
            name="Programming", is_active=True
        )
        course2 = Course.objects.create(
            title="Python Basics",
            course_code="PY101",
            description="Learn Python",
            is_active=True,
        )
        course2.categories.add(programming_category)

        enrollment1 = Enrollment.objects.create(user=self.user, course=self.course)
        enrollment2 = Enrollment.objects.create(user=self.user, course=course2)

        enrollments = list(Enrollment.objects.filter(user=self.user))
        # Most recent first
        self.assertEqual(enrollments[0], enrollment2)
        self.assertEqual(enrollments[1], enrollment1)

    def test_enrollment_auto_enrolled_at_timestamp(self):
        """Test that enrolled_at is automatically set."""
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        self.assertIsNotNone(enrollment.enrolled_at)

        from django.utils import timezone

        self.assertLess(enrollment.enrolled_at, timezone.now())

    def test_enrollment_cascade_delete_user(self):
        """Test that enrollment is deleted when user is deleted."""
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        enrollment_id = enrollment.id

        self.user.delete()

        # Enrollment should be deleted (CASCADE)
        self.assertFalse(Enrollment.objects.filter(id=enrollment_id).exists())

    def test_enrollment_cascade_delete_course(self):
        """Test that enrollment is deleted when course is deleted."""
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        enrollment_id = enrollment.id

        self.course.delete()

        # Enrollment should be deleted (CASCADE)
        self.assertFalse(Enrollment.objects.filter(id=enrollment_id).exists())

    def test_multiple_users_enroll_same_course(self):
        """Test that multiple users can enroll in the same course."""
        user2 = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="password123",
        )

        enrollment1 = Enrollment.objects.create(user=self.user, course=self.course)
        enrollment2 = Enrollment.objects.create(user=user2, course=self.course)

        self.assertNotEqual(enrollment1, enrollment2)
        self.assertEqual(enrollment1.course, enrollment2.course)

    def test_user_enrolls_multiple_courses(self):
        """Test that a user can enroll in multiple courses."""
        programming_category = Category.objects.create(
            name="Programming", is_active=True
        )
        course2 = Course.objects.create(
            title="Python Basics",
            course_code="PY101",
            description="Learn Python",
            is_active=True,
        )
        course2.categories.add(programming_category)

        enrollment1 = Enrollment.objects.create(user=self.user, course=self.course)
        enrollment2 = Enrollment.objects.create(user=self.user, course=course2)

        self.assertNotEqual(enrollment1, enrollment2)
        self.assertEqual(enrollment1.user, enrollment2.user)

    def test_enrollment_related_name_user(self):
        """Test that user.enrollments related name works."""
        Enrollment.objects.create(user=self.user, course=self.course)

        self.assertEqual(self.user.enrollments.count(), 1)
        self.assertEqual(self.user.enrollments.first().course, self.course)

    def test_enrollment_related_name_course(self):
        """Test that course.enrollments related name works."""
        Enrollment.objects.create(user=self.user, course=self.course)

        self.assertEqual(self.course.enrollments.count(), 1)
        self.assertEqual(self.course.enrollments.first().user, self.user)
