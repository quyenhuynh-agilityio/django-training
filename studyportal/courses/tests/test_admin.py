# courses/tests/test_admin.py
from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from courses.models import Course, Category
from courses.admin import CourseAdmin, CategoryAdmin


class CategoryAdminTest(TestCase):
    """Test cases for Category admin."""

    def setUp(self):
        self.site = AdminSite()
        self.category = Category.objects.create(
            name="Web Development",
            description="Web development courses",
            is_active=True,
        )
        self.admin = CategoryAdmin(Category, self.site)

    def test_list_display(self):
        """Test that list_display shows correct fields."""
        self.assertEqual(self.admin.list_display, ("name", "is_active", "created_at"))

    def test_list_filter(self):
        """Test that list_filter is configured correctly."""
        self.assertEqual(self.admin.list_filter, ("is_active",))

    def test_search_fields(self):
        """Test that search_fields is configured correctly."""
        self.assertEqual(self.admin.search_fields, ("name", "description"))

    def test_list_per_page(self):
        """Test that list_per_page is configured."""
        self.assertEqual(self.admin.list_per_page, 20)


class CourseAdminTest(TestCase):
    """Test cases for Course admin."""

    def setUp(self):
        self.site = AdminSite()
        self.category = Category.objects.create(name="Web Development", is_active=True)
        self.course = Course.objects.create(
            title="Django Basics",
            course_code="DJ101",
            description="Learn Django",
            is_active=True,
        )
        self.course.categories.add(self.category)
        self.admin = CourseAdmin(Course, self.site)

    def test_list_display(self):
        """Test that list_display shows correct fields."""
        self.assertEqual(
            self.admin.list_display,
            ("title", "get_categories", "is_active", "created_at"),
        )

    def test_list_filter(self):
        """Test that list_filter is configured correctly."""
        self.assertEqual(self.admin.list_filter, ("categories", "is_active"))

    def test_search_fields(self):
        """Test that search_fields is configured correctly."""
        self.assertEqual(self.admin.search_fields, ("title", "categories__name"))

    def test_filter_horizontal(self):
        """Test that filter_horizontal is configured for categories."""
        self.assertEqual(self.admin.filter_horizontal, ("categories",))

    def test_list_per_page(self):
        """Test that list_per_page is configured."""
        self.assertEqual(self.admin.list_per_page, 20)

    def test_get_categories_method(self):
        """Test that get_categories method returns comma-separated category names."""
        categories_str = self.admin.get_categories(self.course)
        self.assertEqual(categories_str, "Web Development")

    def test_get_categories_multiple(self):
        """Test that get_categories handles multiple categories."""
        category2 = Category.objects.create(name="Programming", is_active=True)
        self.course.categories.add(category2)
        categories_str = self.admin.get_categories(self.course)
        # Order may vary, so just check it contains both
        self.assertIn("Web Development", categories_str)
        self.assertIn("Programming", categories_str)

    def test_soft_delete_courses_action(self):
        """Test that soft_delete_courses action deactivates courses."""
        course2 = Course.objects.create(
            title="Python Basics",
            course_code="PY101",
            description="Learn Python",
            is_active=True,
        )
        course2.categories.add(self.category)

        queryset = Course.objects.filter(id__in=[self.course.id, course2.id])
        request = None  # Admin doesn't require request for this test

        self.admin.soft_delete_courses(request, queryset)

        self.course.refresh_from_db()
        course2.refresh_from_db()
        self.assertFalse(self.course.is_active)
        self.assertFalse(course2.is_active)
