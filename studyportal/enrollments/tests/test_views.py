# enrollments/tests/test_views.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from courses.models import Course, Category
from enrollments.models import Enrollment

User = get_user_model()


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
        self.web_category = Category.objects.create(name="Web", is_active=True)
        self.programming_category = Category.objects.create(
            name="Programming", is_active=True
        )
        self.test_category = Category.objects.create(name="Test", is_active=True)

        # Create test courses
        self.course1 = Course.objects.create(
            title="Django Basics",
            course_code="DJ101",
            description="Learn Django",
            is_active=True,
        )
        self.course1.categories.add(self.web_category)
        self.course2 = Course.objects.create(
            title="Python Basics",
            course_code="PY101",
            description="Learn Python",
            is_active=True,
        )
        self.course2.categories.add(self.programming_category)
        self.course3 = Course.objects.create(
            title="React Fundamentals",
            course_code="RE101",
            description="Learn React",
            is_active=True,
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

    def test_enrolled_courses_shows_active_courses(self):
        """Test that enrolled_courses shows active courses if enrolled."""
        active_course = Course.objects.create(
            title="Active Course",
            course_code="ACT101",
            description="Active",
            is_active=True,
        )
        active_course.categories.add(self.test_category)
        Enrollment.objects.create(user=self.user, course=active_course)

        url = reverse("enrolled_courses")
        response = self.client.get(url)
        courses = response.context["courses"]

        # Should show active courses if enrolled
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0], active_course)

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
