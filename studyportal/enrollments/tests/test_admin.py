# enrollments/tests/test_admin.py
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from courses.models import Course, Category
from enrollments.models import Enrollment
from enrollments.admin import EnrollmentAdmin

User = get_user_model()


class EnrollmentAdminTest(TestCase):
    """Test cases for Enrollment admin."""

    def setUp(self):
        self.site = AdminSite()
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
        self.enrollment = Enrollment.objects.create(
            user=self.user, course=self.course, is_active=True
        )
        self.admin = EnrollmentAdmin(Enrollment, self.site)

    def test_list_display(self):
        """Test that list_display shows correct fields."""
        self.assertEqual(
            self.admin.list_display, ("user", "course", "enrolled_at", "is_active")
        )

    def test_list_filter(self):
        """Test that list_filter is configured correctly."""
        self.assertEqual(self.admin.list_filter, ("course", "is_active"))

    def test_search_fields(self):
        """Test that search_fields is configured correctly."""
        self.assertEqual(self.admin.search_fields, ("user__username", "course__title"))

    def test_has_add_permission_returns_false(self):
        """Test that add permission is disabled."""
        request = None  # Admin doesn't require request for this test
        self.assertFalse(self.admin.has_add_permission(request))

    def test_has_change_permission_returns_false(self):
        """Test that change permission is disabled."""
        request = None
        self.assertFalse(self.admin.has_change_permission(request))

    def test_has_delete_permission_returns_false(self):
        """Test that delete permission is disabled."""
        request = None
        self.assertFalse(self.admin.has_delete_permission(request))

    def test_actions_is_none(self):
        """Test that no actions are available."""
        self.assertIsNone(self.admin.actions)

    def test_get_actions_removes_delete_selected(self):
        """Test that delete_selected action is removed."""
        request = None
        actions = self.admin.get_actions(request)
        self.assertNotIn("delete_selected", actions)
