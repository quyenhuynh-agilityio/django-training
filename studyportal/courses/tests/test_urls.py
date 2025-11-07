# courses/tests/test_urls.py
from django.test import TestCase
from django.urls import reverse, resolve
from courses.views import course_list, enroll_course, enrolled_courses


class CoursesURLsTestCase(TestCase):
    """Test cases for courses URL patterns."""

    def test_course_list_url_resolves(self):
        """Test that course_list URL resolves to correct view."""
        url = reverse("course_list")
        self.assertEqual(url, "/")
        resolved = resolve(url)
        self.assertEqual(resolved.func, course_list)

    def test_enroll_course_url_resolves(self):
        """Test that enroll_course URL resolves to correct view."""
        from courses.models import Course, Category

        category = Category.objects.create(name="Test", is_active=True)
        course = Course.objects.create(
            title="Test Course",
            course_code="TC101",
            description="Test",
            is_active=True,
        )
        course.categories.add(category)

        url = reverse("enroll_course", args=[course.id])
        self.assertIn("/enroll/", url)
        resolved = resolve(url)
        self.assertEqual(resolved.func, enroll_course)

    def test_enrolled_courses_url_resolves(self):
        """Test that enrolled_courses URL resolves to correct view."""
        url = reverse("enrolled_courses")
        self.assertEqual(url, "/my-courses/")
        resolved = resolve(url)
        self.assertEqual(resolved.func, enrolled_courses)

    def test_course_list_url_accessible(self):
        """Test that course_list URL is accessible."""
        url = reverse("course_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
