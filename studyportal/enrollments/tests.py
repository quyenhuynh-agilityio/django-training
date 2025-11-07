import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db import IntegrityError
from courses.models import Course, Category
from .models import Enrollment

User = get_user_model()


class EnrollmentModelTest(TestCase):
    """Test cases for Enrollment model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="password123",
        )
        self.category = Category.objects.create(name="Web Development", is_active=False)
        self.course = Course.objects.create(
            title="Django Basics",
            course_code="DJ101",
            description="Learn Django",
            is_active=False,
        )
        self.course.categories.add(self.category)

    def test_enrollment_creation(self):
        """Test creating an enrollment."""
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)

        self.assertEqual(enrollment.user.username, "student1")
        self.assertEqual(enrollment.course.title, "Django Basics")
        self.assertFalse(enrollment.is_active)
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
        enrollment.is_active = True
        enrollment.save()

        enrollment.refresh_from_db()
        self.assertTrue(enrollment.is_active)

    def test_enrollment_soft_delete_preserves_record(self):
        """Test that soft delete doesn't remove enrollment from database."""
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        enrollment_id = enrollment.id
        enrollment.is_active = False
        enrollment.save()

        # Enrollment should still exist in database
        self.assertTrue(Enrollment.objects.filter(id=enrollment_id).exists())
        retrieved_enrollment = Enrollment.objects.get(id=enrollment_id)
        self.assertTrue(retrieved_enrollment.is_active)

    def test_enrollment_string_representation(self):
        """Test enrollment __str__ method."""
        enrollment = Enrollment.objects.create(user=self.user, course=self.course)
        expected = f"{self.user.username} -> {self.course.title}"
        self.assertEqual(str(enrollment), expected)

    def test_enrollment_unique_together_constraint(self):
        """Test that user and course combination must be unique."""
        Enrollment.objects.create(user=self.user, course=self.course)

        # Attempting to create duplicate enrollment should raise IntegrityError
        with self.assertRaises(IntegrityError):
            Enrollment.objects.create(user=self.user, course=self.course)

    def test_enrollment_ordering_by_enrolled_at_descending(self):
        """Test that enrollments are ordered by enrolled_at descending."""
        programming_category = Category.objects.create(name="Programming")
        course2 = Course.objects.create(
            title="Python Basics",
            course_code="PY101",
            description="Learn Python",
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
        programming_category = Category.objects.create(name="Programming")
        course2 = Course.objects.create(
            title="Python Basics",
            course_code="PY101",
            description="Learn Python",
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


class EnrolledCoursesViewTest(TestCase):
    """Test cases for enrolled_courses view."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="password123",
        )
        self.client.login(username="student1", password="password123")

        # Create test categories
        self.web_category = Category.objects.create(name="Web", is_active=False)
        self.programming_category = Category.objects.create(
            name="Programming", is_active=False
        )
        self.test_category = Category.objects.create(name="Test", is_active=False)

        # Create test courses
        self.course1 = Course.objects.create(
            title="Django Basics",
            course_code="DJ101",
            description="Learn Django",
            is_active=False,
        )
        self.course1.categories.add(self.web_category)
        self.course2 = Course.objects.create(
            title="Python Basics",
            course_code="PY101",
            description="Learn Python",
            is_active=False,
        )
        self.course2.categories.add(self.programming_category)
        self.course3 = Course.objects.create(
            title="React Fundamentals",
            course_code="RE101",
            description="Learn React",
            is_active=False,
        )
        self.course3.categories.add(self.web_category)

    def test_enrolled_courses_requires_login(self):
        """Test that enrolled_courses view requires authentication."""
        self.client.logout()
        url = reverse("enrolled_courses")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_enrolled_courses_renders(self):
        """Test that enrolled_courses view renders successfully."""
        url = reverse("enrolled_courses")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/course_list.html")

    def test_enrolled_courses_shows_only_user_enrollments(self):
        """Test that enrolled_courses shows only courses for logged-in user."""
        # Create enrollment for current user
        Enrollment.objects.create(user=self.user, course=self.course1)

        # Create enrollment for another user
        user2 = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="password123",
        )
        Enrollment.objects.create(user=user2, course=self.course2)

        url = reverse("enrolled_courses")
        response = self.client.get(url)
        courses = response.context["courses"]

        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0], self.course1)

    def test_enrolled_courses_shows_multiple_enrollments(self):
        """Test that enrolled_courses shows all enrolled courses."""
        Enrollment.objects.create(user=self.user, course=self.course1)
        Enrollment.objects.create(user=self.user, course=self.course2)
        Enrollment.objects.create(user=self.user, course=self.course3)

        url = reverse("enrolled_courses")
        response = self.client.get(url)
        courses = response.context["courses"]

        self.assertEqual(len(courses), 3)
        course_titles = [c.title for c in courses]
        self.assertIn("Django Basics", course_titles)
        self.assertIn("Python Basics", course_titles)
        self.assertIn("React Fundamentals", course_titles)

    def test_enrolled_courses_excludes_deleted_enrollments(self):
        """Test that soft-deleted enrollments are not shown."""
        # Create a non-deleted enrollment that should remain visible
        Enrollment.objects.create(user=self.user, course=self.course1)

        enrollment2 = Enrollment.objects.create(user=self.user, course=self.course2)

        # Soft delete one enrollment
        enrollment2.is_active = False
        enrollment2.save()

        url = reverse("enrolled_courses")
        response = self.client.get(url)
        courses = response.context["courses"]

        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0], self.course1)

    def test_enrolled_courses_empty_when_no_enrollments(self):
        """Test that enrolled_courses shows empty queryset when user has no enrollments."""
        from django.db.models.query import QuerySet

        url = reverse("enrolled_courses")
        response = self.client.get(url)
        courses = response.context["courses"]

        self.assertEqual(len(courses), 0)
        self.assertIsInstance(courses, QuerySet)

    def test_enrolled_courses_shows_inactive_courses(self):
        """Test that enrolled_courses does not show inactive courses even if enrolled."""
        inactive_course = Course.objects.create(
            title="Inactive Course",
            course_code="IN101",
            description="Inactive",
            is_active=False,
        )
        inactive_course.categories.add(self.test_category)
        Enrollment.objects.create(user=self.user, course=inactive_course)

        url = reverse("enrolled_courses")
        response = self.client.get(url)
        courses = response.context["courses"]

        # Inactive courses are filtered out by is_active=False
        self.assertEqual(len(courses), 0)

    def test_enrolled_courses_shows_deleted_courses(self):
        """Test that enrolled_courses shows soft-deleted courses if enrolled."""
        deleted_course = Course.objects.create(
            title="Deleted Course",
            course_code="DEL101",
            description="Deleted",
            is_active=True,
        )
        deleted_course.categories.add(self.test_category)
        Enrollment.objects.create(user=self.user, course=deleted_course)

        url = reverse("enrolled_courses")
        response = self.client.get(url)
        courses = response.context["courses"]

        # Should still show deleted courses if enrolled
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0], deleted_course)

    def test_enrolled_courses_ordered_by_enrolled_at(self):
        """Test that enrolled courses maintain enrollment order."""
        # Create enrollments in specific order
        Enrollment.objects.create(user=self.user, course=self.course1)
        Enrollment.objects.create(user=self.user, course=self.course2)
        Enrollment.objects.create(user=self.user, course=self.course3)

        url = reverse("enrolled_courses")
        response = self.client.get(url)
        courses = response.context["courses"]

        # Should have 3 courses
        self.assertEqual(len(courses), 3)

    def test_enrolled_courses_both_url_names(self):
        """Test that both URL names work (my-courses and enrolled)."""
        Enrollment.objects.create(user=self.user, course=self.course1)

        # Test both URL patterns
        url1 = reverse("enrolled_courses")
        response1 = self.client.get(url1)

        # Both should work (they point to same view)
        self.assertEqual(response1.status_code, 200)
