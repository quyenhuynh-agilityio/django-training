"""
Comprehensive tests for core utility functions.
"""

import uuid
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from core.utils import (
    get_course_filter_params,
    filter_courses_by_category,
    get_categories_for_courses,
    get_courses_for_user,
    build_course_list_context,
)
from courses.models import Course, Category
from enrollments.models import Enrollment

User = get_user_model()


class GetCourseFilterParamsTestCase(TestCase):
    """Test get_course_filter_params function."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_get_params_with_all_values(self):
        """Test extracting all filter parameters."""
        request = self.factory.get("/courses/?q=python&category=123&page=2")
        query, category, page_number = get_course_filter_params(request)
        self.assertEqual(query, "python")
        self.assertEqual(category, "123")
        self.assertEqual(page_number, "2")

    def test_get_params_with_empty_values(self):
        """Test with no query parameters."""
        request = self.factory.get("/courses/")
        query, category, page_number = get_course_filter_params(request)
        self.assertEqual(query, "")
        self.assertEqual(category, "")
        self.assertEqual(page_number, 1)

    def test_get_params_strips_whitespace(self):
        """Test that whitespace is stripped from parameters."""
        request = self.factory.get("/courses/?q=  python  &category=  123  ")
        query, category, page_number = get_course_filter_params(request)
        self.assertEqual(query, "python")
        self.assertEqual(category, "123")

    def test_get_params_with_only_query(self):
        """Test with only query parameter."""
        request = self.factory.get("/courses/?q=django")
        query, category, page_number = get_course_filter_params(request)
        self.assertEqual(query, "django")
        self.assertEqual(category, "")
        self.assertEqual(page_number, 1)

    def test_get_params_with_only_category(self):
        """Test with only category parameter."""
        request = self.factory.get("/courses/?category=abc-123")
        query, category, page_number = get_course_filter_params(request)
        self.assertEqual(query, "")
        self.assertEqual(category, "abc-123")
        self.assertEqual(page_number, 1)


class FilterCoursesByCategoryTestCase(TestCase):
    """Test filter_courses_by_category function."""

    def setUp(self):
        self.category1 = Category.objects.create(name="Programming", is_active=True)
        self.category2 = Category.objects.create(name="Design", is_active=True)
        self.category_inactive = Category.objects.create(name="Old", is_active=False)
        self.course1 = Course.objects.create(
            title="Python Basics", course_code="PY101", description="Learn Python"
        )
        self.course1.categories.add(self.category1)
        self.course2 = Course.objects.create(
            title="Web Design", course_code="WD101", description="Learn Design"
        )
        self.course2.categories.add(self.category2)
        self.course3 = Course.objects.create(
            title="Advanced Python", course_code="PY201", description="Advanced Python"
        )
        self.course3.categories.add(self.category1)

    def test_filter_with_valid_category_uuid(self):
        """Test filtering with a valid active category UUID."""
        courses = Course.objects.all()
        courses, category_name, category = filter_courses_by_category(
            courses, str(self.category1.id)
        )
        self.assertEqual(category_name, "Programming")
        self.assertEqual(category, str(self.category1.id))
        self.assertEqual(courses.count(), 2)
        self.assertIn(self.course1, courses)
        self.assertIn(self.course3, courses)
        self.assertNotIn(self.course2, courses)

    def test_filter_with_empty_category(self):
        """Test filtering with empty category string."""
        courses = Course.objects.all()
        courses, category_name, category = filter_courses_by_category(courses, "")
        self.assertEqual(category_name, "")
        self.assertEqual(category, "")
        self.assertEqual(courses.count(), 3)

    def test_filter_with_invalid_uuid(self):
        """Test filtering with invalid UUID format."""
        courses = Course.objects.all()
        courses, category_name, category = filter_courses_by_category(
            courses, "invalid"
        )
        self.assertEqual(category_name, "")
        self.assertEqual(category, "")
        self.assertEqual(courses.count(), 0)

    def test_filter_with_nonexistent_category(self):
        """Test filtering with non-existent category UUID."""
        fake_uuid = str(uuid.uuid4())
        courses = Course.objects.all()
        courses, category_name, category = filter_courses_by_category(
            courses, fake_uuid
        )
        self.assertEqual(category_name, "")
        self.assertEqual(category, "")
        self.assertEqual(courses.count(), 0)

    def test_filter_with_inactive_category(self):
        """Test filtering with inactive category."""
        courses = Course.objects.all()
        courses, category_name, category = filter_courses_by_category(
            courses, str(self.category_inactive.id)
        )
        self.assertEqual(category_name, "")
        self.assertEqual(category, "")
        self.assertEqual(courses.count(), 0)


class GetCategoriesForCoursesTestCase(TestCase):
    """Test get_categories_for_courses function."""

    def setUp(self):
        self.category1 = Category.objects.create(name="Programming", is_active=True)
        self.category2 = Category.objects.create(name="Design", is_active=True)
        self.category_inactive = Category.objects.create(name="Old", is_active=False)
        self.course1 = Course.objects.create(
            title="Python Basics",
            course_code="PY101",
            description="Learn Python",
            is_active=True,
        )
        self.course1.categories.add(self.category1)
        self.course2 = Course.objects.create(
            title="Web Design",
            course_code="WD101",
            description="Learn Design",
            is_active=True,
        )
        self.course2.categories.add(self.category2)
        self.course_inactive = Course.objects.create(
            title="Old Course", course_code="OLD101", description="Old", is_active=False
        )
        self.course_inactive.categories.add(self.category_inactive)

    def test_get_categories_without_course_ids(self):
        """Test getting categories for all active courses."""
        categories = get_categories_for_courses()
        self.assertEqual(categories.count(), 2)
        self.assertIn(self.category1, categories)
        self.assertIn(self.category2, categories)
        self.assertNotIn(self.category_inactive, categories)
        # Check ordering
        self.assertEqual(list(categories), [self.category2, self.category1])

    def test_get_categories_with_specific_course_ids(self):
        """Test getting categories for specific courses."""
        categories = get_categories_for_courses([self.course1.id])
        self.assertEqual(categories.count(), 1)
        self.assertIn(self.category1, categories)
        self.assertNotIn(self.category2, categories)

    def test_get_categories_with_multiple_course_ids(self):
        """Test getting categories for multiple courses."""
        categories = get_categories_for_courses([self.course1.id, self.course2.id])
        self.assertEqual(categories.count(), 2)
        self.assertIn(self.category1, categories)
        self.assertIn(self.category2, categories)

    def test_get_categories_with_empty_list(self):
        """Test getting categories with empty course_ids list."""
        categories = get_categories_for_courses([])
        self.assertEqual(categories.count(), 0)

    def test_get_categories_excludes_inactive_courses(self):
        """Test that inactive courses are excluded."""
        categories = get_categories_for_courses()
        self.assertNotIn(self.category_inactive, categories)


class GetCoursesForUserTestCase(TestCase):
    """Test get_courses_for_user function."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student1", email="student1@example.com", password="pass123"
        )
        self.staff_user = User.objects.create_user(
            username="staff1",
            email="staff1@example.com",
            password="pass123",
            is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="admin123"
        )
        self.course1 = Course.objects.create(
            title="Python Basics",
            course_code="PY101",
            description="Learn Python",
            is_active=True,
        )
        self.course2 = Course.objects.create(
            title="Django Advanced",
            course_code="DJ201",
            description="Advanced Django",
            is_active=True,
        )
        self.course_inactive = Course.objects.create(
            title="Old Course", course_code="OLD101", description="Old", is_active=False
        )

    def test_get_courses_for_anonymous_user(self):
        """Test getting courses for anonymous user."""
        from django.contrib.auth.models import AnonymousUser

        anonymous = AnonymousUser()
        courses = get_courses_for_user(anonymous)
        self.assertEqual(courses.count(), 2)
        self.assertIn(self.course1, courses)
        self.assertIn(self.course2, courses)
        self.assertNotIn(self.course_inactive, courses)

    def test_get_courses_for_regular_user(self):
        """Test getting courses for regular authenticated user."""
        courses = get_courses_for_user(self.user)
        self.assertEqual(courses.count(), 2)
        self.assertIn(self.course1, courses)
        self.assertIn(self.course2, courses)
        self.assertNotIn(self.course_inactive, courses)

    def test_get_courses_for_staff_user(self):
        """Test getting courses for staff user."""
        courses = get_courses_for_user(self.staff_user)
        # Staff should see all courses including inactive
        self.assertEqual(courses.count(), 3)
        self.assertIn(self.course1, courses)
        self.assertIn(self.course2, courses)
        self.assertIn(self.course_inactive, courses)

    def test_get_courses_for_superuser(self):
        """Test getting courses for superuser."""
        courses = get_courses_for_user(self.superuser)
        # Superuser should see all courses including inactive
        self.assertEqual(courses.count(), 3)
        self.assertIn(self.course1, courses)
        self.assertIn(self.course2, courses)
        self.assertIn(self.course_inactive, courses)

    def test_get_courses_enrolled_only_for_anonymous(self):
        """Test enrolled_only mode for anonymous user."""
        from django.contrib.auth.models import AnonymousUser

        anonymous = AnonymousUser()
        courses = get_courses_for_user(anonymous, enrolled_only=True)
        self.assertEqual(courses.count(), 0)

    def test_get_courses_enrolled_only_for_user_with_enrollments(self):
        """Test enrolled_only mode for user with enrollments."""
        Enrollment.objects.create(user=self.user, course=self.course1, is_active=True)
        courses = get_courses_for_user(self.user, enrolled_only=True)
        self.assertEqual(courses.count(), 1)
        self.assertIn(self.course1, courses)
        self.assertNotIn(self.course2, courses)

    def test_get_courses_enrolled_only_excludes_inactive_enrollments(self):
        """Test that inactive enrollments are excluded."""
        Enrollment.objects.create(user=self.user, course=self.course1, is_active=False)
        courses = get_courses_for_user(self.user, enrolled_only=True)
        self.assertEqual(courses.count(), 0)

    def test_get_courses_enrolled_only_excludes_inactive_courses(self):
        """Test that inactive courses are excluded even if enrolled."""
        Enrollment.objects.create(
            user=self.user, course=self.course_inactive, is_active=True
        )
        courses = get_courses_for_user(self.user, enrolled_only=True)
        self.assertEqual(courses.count(), 0)


class BuildCourseListContextTestCase(TestCase):
    """Test build_course_list_context function."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="student1", email="student1@example.com", password="pass123"
        )
        self.category1 = Category.objects.create(name="Programming", is_active=True)
        self.category2 = Category.objects.create(name="Design", is_active=True)
        self.course1 = Course.objects.create(
            title="Python Basics",
            course_code="PY101",
            description="Learn Python",
            is_active=True,
        )
        self.course1.categories.add(self.category1)
        self.course2 = Course.objects.create(
            title="Django Advanced",
            course_code="DJ201",
            description="Advanced Django",
            is_active=True,
        )
        self.course2.categories.add(self.category1)
        self.course3 = Course.objects.create(
            title="Web Design",
            course_code="WD101",
            description="Learn Design",
            is_active=True,
        )
        self.course3.categories.add(self.category2)

    def test_build_context_with_no_filters(self):
        """Test building context with no filters."""
        request = self.factory.get("/courses/")
        request.user = self.user
        courses = Course.objects.filter(is_active=True)
        context = build_course_list_context(request, courses)
        self.assertEqual(context["query"], "")
        self.assertEqual(context["category"], "")
        self.assertEqual(context["category_name"], "")
        self.assertEqual(len(context["courses"]), 3)
        self.assertIsNotNone(context["page_obj"])
        self.assertIsNotNone(context["categories"])

    def test_build_context_with_query_filter(self):
        """Test building context with query filter."""
        request = self.factory.get("/courses/?q=Python")
        request.user = self.user
        courses = Course.objects.filter(is_active=True)
        context = build_course_list_context(request, courses)
        self.assertEqual(context["query"], "Python")
        self.assertEqual(len(context["courses"]), 1)
        self.assertIn(self.course1, context["courses"])

    def test_build_context_with_category_filter(self):
        """Test building context with category filter."""
        request = self.factory.get(f"/courses/?category={self.category1.id}")
        request.user = self.user
        courses = Course.objects.filter(is_active=True)
        context = build_course_list_context(request, courses)
        self.assertEqual(context["category"], str(self.category1.id))
        self.assertEqual(context["category_name"], "Programming")
        self.assertEqual(len(context["courses"]), 2)
        self.assertIn(self.course1, context["courses"])
        self.assertIn(self.course2, context["courses"])

    def test_build_context_with_query_and_category(self):
        """Test building context with both query and category filters."""
        request = self.factory.get(f"/courses/?q=Python&category={self.category1.id}")
        request.user = self.user
        courses = Course.objects.filter(is_active=True)
        context = build_course_list_context(request, courses)
        self.assertEqual(context["query"], "Python")
        self.assertEqual(context["category"], str(self.category1.id))
        self.assertEqual(len(context["courses"]), 1)
        self.assertIn(self.course1, context["courses"])

    def test_build_context_with_pagination(self):
        """Test building context with pagination."""
        request = self.factory.get("/courses/?page=1")
        request.user = self.user
        courses = Course.objects.filter(is_active=True)
        context = build_course_list_context(request, courses, page_size=2)
        self.assertEqual(len(context["courses"]), 2)
        self.assertTrue(context["page_obj"].has_next())
        self.assertFalse(context["page_obj"].has_previous())

    def test_build_context_with_enrolled_ids_provided(self):
        """Test building context with enrolled_ids provided."""
        Enrollment.objects.create(user=self.user, course=self.course1, is_active=True)
        request = self.factory.get("/courses/")
        request.user = self.user
        courses = Course.objects.filter(is_active=True)
        enrolled_ids = [self.course1.id]
        context = build_course_list_context(request, courses, enrolled_ids=enrolled_ids)
        self.assertEqual(context["enrolled_ids"], enrolled_ids)

    def test_build_context_auto_fetches_enrolled_ids(self):
        """Test that context auto-fetches enrolled_ids for authenticated user."""
        Enrollment.objects.create(user=self.user, course=self.course1, is_active=True)
        request = self.factory.get("/courses/")
        request.user = self.user
        courses = Course.objects.filter(is_active=True)
        context = build_course_list_context(request, courses)
        self.assertIn(self.course1.id, context["enrolled_ids"])
        self.assertNotIn(self.course2.id, context["enrolled_ids"])

    def test_build_context_with_anonymous_user(self):
        """Test building context for anonymous user."""
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get("/courses/")
        request.user = AnonymousUser()
        courses = Course.objects.filter(is_active=True)
        context = build_course_list_context(request, courses)
        self.assertEqual(context["enrolled_ids"], [])
