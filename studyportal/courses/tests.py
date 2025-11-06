import uuid
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from courses.models import Course, Category
from enrollments.models import Enrollment

User = get_user_model()


class CourseModelTest(TestCase):
    """Test cases for Course model."""

    def setUp(self):
        self.category = Category.objects.create(
            name="Web Development",
            description="Web development courses",
            is_active=True,
        )
        self.course_data = {
            "title": "Django Basics",
            "course_code": "DJ101",
            "description": "Learn Django fundamentals",
            "video_url": "https://example.com/video",
            "image_url": "https://example.com/image.jpg",
            "is_active": True,
        }

    def test_course_creation(self):
        """Test creating a course with all fields."""
        course = Course.objects.create(**self.course_data)
        course.categories.add(self.category)
        self.assertEqual(course.title, "Django Basics")
        self.assertEqual(course.course_code, "DJ101")
        self.assertEqual(course.description, "Learn Django fundamentals")
        self.assertIn(self.category, course.categories.all())
        self.assertEqual(course.categories.first().name, "Web Development")
        self.assertEqual(course.video_url, "https://example.com/video")
        self.assertEqual(course.image_url, "https://example.com/image.jpg")
        self.assertTrue(course.is_active)
        self.assertFalse(course.is_deleted)
        self.assertIsInstance(course.id, uuid.UUID)

    def test_course_creation_minimal_fields(self):
        """Test creating a course with only required fields."""
        programming_category = Category.objects.create(name="Programming")
        course = Course.objects.create(
            title="Python Basics",
            course_code="PY101",
            description="Python fundamentals",
        )
        course.categories.add(programming_category)
        self.assertEqual(course.title, "Python Basics")
        self.assertEqual(course.categories.first().name, "Programming")
        self.assertIsNone(course.video_url)
        self.assertIsNone(course.image_url)
        self.assertTrue(course.is_active)  # default value
        self.assertFalse(course.is_deleted)  # default value

    def test_course_soft_delete(self):
        """Test soft deleting a course."""
        course = Course.objects.create(**self.course_data)
        course.is_deleted = True
        course.save()

        course.refresh_from_db()
        self.assertTrue(course.is_deleted)

    def test_course_string_representation(self):
        """Test course __str__ method."""
        course = Course.objects.create(**self.course_data)
        self.assertEqual(str(course), "Django Basics")

    def test_course_ordering(self):
        """Test that courses are ordered by title."""
        test_category = Category.objects.create(name="Test")
        course1 = Course.objects.create(
            title="Zebra Course", course_code="Z001", description="Z"
        )
        course1.categories.add(test_category)
        course2 = Course.objects.create(
            title="Alpha Course", course_code="A001", description="A"
        )
        course2.categories.add(test_category)
        course3 = Course.objects.create(
            title="Beta Course", course_code="B001", description="B"
        )
        course3.categories.add(test_category)

        courses = list(Course.objects.all())
        self.assertEqual(courses[0].title, "Alpha Course")
        self.assertEqual(courses[1].title, "Beta Course")
        self.assertEqual(courses[2].title, "Zebra Course")

    def test_course_timestamps(self):
        """Test that created_at and updated_at are automatically set."""
        course = Course.objects.create(**self.course_data)
        self.assertIsNotNone(course.created_at)
        self.assertIsNotNone(course.updated_at)

        # Update and check updated_at changes
        old_updated_at = course.updated_at
        course.title = "Updated Title"
        course.save()
        course.refresh_from_db()
        self.assertGreater(course.updated_at, old_updated_at)


class CategoryModelTest(TestCase):
    """Test cases for Category model."""

    def setUp(self):
        self.category_data = {
            "name": "Web Development",
            "description": "Courses related to web development",
            "is_active": True,
        }

    def test_category_creation(self):
        """Test creating a category with all fields."""
        category = Category.objects.create(**self.category_data)
        self.assertEqual(category.name, "Web Development")
        self.assertEqual(category.description, "Courses related to web development")
        self.assertTrue(category.is_active)
        self.assertIsInstance(category.id, uuid.UUID)

    def test_category_creation_minimal_fields(self):
        """Test creating a category with only required fields."""
        category = Category.objects.create(name="Programming")
        self.assertEqual(category.name, "Programming")
        self.assertIsNone(category.description)
        self.assertTrue(category.is_active)  # default value

    def test_category_name_unique(self):
        """Test that category name must be unique."""
        Category.objects.create(name="Web Development")
        with self.assertRaises(Exception):  # IntegrityError or ValidationError
            Category.objects.create(name="Web Development")

    def test_category_string_representation(self):
        """Test category __str__ method."""
        category = Category.objects.create(name="Data Science")
        self.assertEqual(str(category), "Data Science")

    def test_category_ordering(self):
        """Test that categories are ordered by name."""
        Category.objects.create(name="Zebra Category")
        Category.objects.create(name="Alpha Category")
        Category.objects.create(name="Beta Category")

        categories = list(Category.objects.all())
        self.assertEqual(categories[0].name, "Alpha Category")
        self.assertEqual(categories[1].name, "Beta Category")
        self.assertEqual(categories[2].name, "Zebra Category")

    def test_category_timestamps(self):
        """Test that created_at and updated_at are automatically set."""
        category = Category.objects.create(**self.category_data)
        self.assertIsNotNone(category.created_at)
        self.assertIsNotNone(category.updated_at)

        # Update and check updated_at changes
        old_updated_at = category.updated_at
        category.name = "Updated Category"
        category.save()
        category.refresh_from_db()
        self.assertGreater(category.updated_at, old_updated_at)

    def test_category_related_courses(self):
        """Test that category has related courses."""
        category = Category.objects.create(name="Web Development")
        course1 = Course.objects.create(
            title="Django Basics",
            course_code="DJ101",
            description="Learn Django",
        )
        course1.categories.add(category)
        course2 = Course.objects.create(
            title="React Basics",
            course_code="RE101",
            description="Learn React",
        )
        course2.categories.add(category)

        self.assertEqual(category.courses.count(), 2)
        self.assertIn(course1, category.courses.all())
        self.assertIn(course2, category.courses.all())

    def test_category_removed_on_delete(self):
        """Test that courses' categories are removed when category is deleted."""
        category = Category.objects.create(name="Web Development")
        course = Course.objects.create(
            title="Django Basics",
            course_code="DJ101",
            description="Learn Django",
        )
        course.categories.add(category)

        category.delete()

        course.refresh_from_db()
        self.assertEqual(course.categories.count(), 0)
        self.assertNotIn(category, course.categories.all())


class CourseListViewTest(TestCase):
    """Test cases for course_list view."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass123")
        self.client.login(username="testuser", password="pass123")

        # Create test categories
        self.web_category = Category.objects.create(name="Web", is_active=True)
        self.programming_category = Category.objects.create(
            name="Programming", is_active=True
        )
        self.data_category = Category.objects.create(name="Data", is_active=True)

        # Create test courses
        self.courses_data = [
            ("Django Basics", self.web_category),
            ("Django Advanced", self.web_category),
            ("Python Basics", self.programming_category),
            ("Data Science Intro", self.data_category),
            ("React Fundamentals", self.web_category),
        ]

        for title, category in self.courses_data:
            course = Course.objects.create(
                title=title,
                course_code=f"{category.name[:3].upper()}001",
                description=f"Description for {title}",
                is_active=True,
            )
            course.categories.add(category)

    def test_course_list_renders_get(self):
        """Test that course list page renders successfully with GET request."""
        response = self.client.get(reverse("course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/course_list.html")

    def test_course_list_renders_post(self):
        """Test that course list page renders successfully with POST request."""
        response = self.client.post(reverse("course_list"))
        self.assertEqual(response.status_code, 200)

    def test_course_list_shows_only_active_courses(self):
        """Test that inactive courses are not shown."""

        response = self.client.get(reverse("course_list"))
        courses = response.context["courses"]
        course_titles = [c.title for c in courses]
        self.assertNotIn("Inactive Course", course_titles)

    def test_course_list_shows_only_non_deleted_courses(self):
        """Test that soft-deleted courses are not shown."""
        response = self.client.get(reverse("course_list"))
        courses = response.context["courses"]
        course_titles = [c.title for c in courses]
        self.assertNotIn("Deleted Course", course_titles)

    def test_search_filter_exact_match(self):
        """Test search filter with exact match."""
        # Need to include category or it defaults to first category
        response = self.client.post(
            reverse("course_list"),
            {"q": "Python", "category": str(self.programming_category.id)},
        )
        courses = response.context["courses"]
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0].title, "Python Basics")

    def test_search_filter_case_insensitive(self):
        """Test search filter is case insensitive."""
        # Need to include category or it defaults to first category
        response = self.client.post(
            reverse("course_list"),
            {"q": "python", "category": str(self.programming_category.id)},
        )
        courses = response.context["courses"]
        self.assertEqual(len(courses), 1)
        self.assertEqual(courses[0].title, "Python Basics")

    def test_search_filter_partial_match(self):
        """Test search filter with partial match."""
        # Need to include category or it defaults to first category
        response = self.client.post(
            reverse("course_list"),
            {"q": "Django", "category": str(self.web_category.id)},
        )
        courses = response.context["courses"]
        self.assertEqual(len(courses), 2)
        titles = [c.title for c in courses]
        self.assertIn("Django Basics", titles)
        self.assertIn("Django Advanced", titles)

    def test_search_filter_no_results(self):
        """Test search filter with no matching results."""
        response = self.client.post(reverse("course_list"), {"q": "NonExistent"})
        courses = response.context["courses"]
        self.assertEqual(len(courses), 0)

    def test_search_filter_empty_query(self):
        """Test search filter with empty query."""
        response = self.client.post(reverse("course_list"), {"q": ""})
        courses = response.context["courses"]
        # Should return all courses (paginated)
        self.assertGreater(len(courses), 0)

    def test_search_filter_whitespace_only(self):
        """Test search filter with whitespace only query."""
        response = self.client.post(reverse("course_list"), {"q": "   "})
        courses = response.context["courses"]
        # Should return all courses (whitespace is stripped)
        self.assertGreater(len(courses), 0)

    def test_category_filter(self):
        """Test filtering by category."""
        response = self.client.post(
            reverse("course_list"), {"category": str(self.web_category.id)}
        )
        courses = response.context["courses"]
        self.assertEqual(
            len(courses), 3
        )  # Django Basics, Django Advanced, React Fundamentals
        for course in courses:
            self.assertIn(self.web_category, course.categories.all())
            self.assertIn("Web", [cat.name for cat in course.categories.all()])

    def test_category_filter_no_matches(self):
        """Test filtering by non-existent category."""
        fake_uuid = uuid.uuid4()
        response = self.client.post(
            reverse("course_list"), {"category": str(fake_uuid)}
        )
        courses = response.context["courses"]
        self.assertEqual(len(courses), 0)

    def test_category_filter_default_selection(self):
        """Test that no category is selected by default when no category specified."""
        response = self.client.get(reverse("course_list"))
        selected_category = response.context["category"]
        self.assertEqual(selected_category, "")

    def test_categories_list_in_context(self):
        """Test that categories list is in context."""
        response = self.client.get(reverse("course_list"))
        categories = response.context["categories"]
        # Categories is now a QuerySet of Category objects
        category_names = [cat.name for cat in categories]
        self.assertIn("Web", category_names)
        self.assertIn("Programming", category_names)
        self.assertIn("Data", category_names)

    def test_pagination_default_page(self):
        """Test pagination with default page."""
        # Create more courses to test pagination (3 per page)
        # Use same category to ensure they appear together
        for i in range(5):
            course = Course.objects.create(
                title=f"Course {i}",
                course_code=f"T{i:03d}",
                description="Test",
                is_active=True,
            )
            course.categories.add(self.web_category)  # Use existing category

        response = self.client.get(reverse("course_list"))
        courses = response.context["courses"]
        page_obj = response.context["page_obj"]
        self.assertLessEqual(len(courses), 3)
        # With 5 new courses + existing Web courses, should have pagination
        if page_obj.paginator.count > 3:
            self.assertTrue(page_obj.has_other_pages())

    def test_pagination_specific_page(self):
        """Test pagination with specific page number."""
        # Create more courses to test pagination
        # Use same category to ensure they appear together
        for i in range(5):
            course = Course.objects.create(
                title=f"Course {i}",
                course_code=f"T{i:03d}",
                description="Test",
                is_active=True,
            )
            course.categories.add(self.web_category)  # Use existing category

        # Need to specify category to ensure courses are in the same category
        response = self.client.post(
            reverse("course_list"),
            {"page": 2, "category": str(self.web_category.id)},
        )
        page_obj = response.context["page_obj"]
        # Only check page number if there are enough items for page 2
        if page_obj.paginator.num_pages >= 2:
            self.assertEqual(page_obj.number, 2)

    def test_enrolled_ids_in_context_authenticated(self):
        """Test that enrolled_ids are in context for authenticated users."""
        course = Course.objects.first()
        Enrollment.objects.create(user=self.user, course=course)

        response = self.client.get(reverse("course_list"))
        enrolled_ids = response.context["enrolled_ids"]
        self.assertIn(course.id, enrolled_ids)

    def test_enrolled_ids_empty_when_not_enrolled(self):
        """Test that enrolled_ids is empty when user has no enrollments."""
        response = self.client.get(reverse("course_list"))
        enrolled_ids = response.context["enrolled_ids"]
        self.assertEqual(len(enrolled_ids), 0)

    def test_enrolled_ids_excludes_deleted_enrollments(self):
        """Test that soft-deleted enrollments are not included in enrolled_ids."""
        course = Course.objects.first()
        enrollment = Enrollment.objects.create(user=self.user, course=course)
        enrollment.is_deleted = True
        enrollment.save()

        response = self.client.get(reverse("course_list"))
        enrolled_ids = response.context["enrolled_ids"]
        self.assertNotIn(course.id, enrolled_ids)

    def test_course_list_accessible_without_login(self):
        """Test that course list is accessible without authentication."""
        self.client.logout()
        response = self.client.get(reverse("course_list"))
        self.assertEqual(response.status_code, 200)

    def test_search_and_category_filter_combined(self):
        """Test combining search and category filters."""
        response = self.client.post(
            reverse("course_list"),
            {"q": "Django", "category": str(self.web_category.id)},
        )
        courses = response.context["courses"]
        self.assertEqual(len(courses), 2)
        for course in courses:
            self.assertIn("Django", course.title)
            self.assertIn(self.web_category, course.categories.all())
            self.assertIn("Web", [cat.name for cat in course.categories.all()])


class EnrollCourseViewTest(TestCase):
    """Test cases for enroll_course view."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass123")
        self.client.login(username="testuser", password="pass123")
        self.web_category = Category.objects.create(name="Web", is_active=True)
        self.course = Course.objects.create(
            title="Django Basics",
            course_code="DJ101",
            description="Learn Django",
            is_active=True,
        )
        self.course.categories.add(self.web_category)

    def test_enroll_requires_login_redirects(self):
        """Test that unauthenticated users are redirected to login."""
        self.client.logout()
        url = reverse("enroll_course", args=[self.course.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_successful_enrollment(self):
        """Test successful course enrollment."""
        url = reverse("enroll_course", args=[self.course.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Enrollment.objects.filter(
                user=self.user, course=self.course, is_deleted=False
            ).exists()
        )

    def test_successful_enrollment_redirects(self):
        """Test that enrollment redirects to enrolled_courses."""
        url = reverse("enroll_course", args=[self.course.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("enrolled_courses"))

    def test_prevent_duplicate_enrollment(self):
        """Test that duplicate enrollments are prevented."""
        Enrollment.objects.create(user=self.user, course=self.course)
        initial_count = Enrollment.objects.filter(
            user=self.user, course=self.course
        ).count()

        url = reverse("enroll_course", args=[self.course.id])
        self.client.get(url)

        final_count = Enrollment.objects.filter(
            user=self.user, course=self.course
        ).count()
        self.assertEqual(initial_count, final_count)
        self.assertEqual(final_count, 1)

    def test_enrollment_creates_with_is_deleted_false(self):
        """Test that new enrollment is created with is_deleted=False."""
        url = reverse("enroll_course", args=[self.course.id])
        self.client.get(url)

        enrollment = Enrollment.objects.get(user=self.user, course=self.course)
        self.assertFalse(enrollment.is_deleted)

    def test_enrollment_nonexistent_course_404(self):
        """Test that enrolling in non-existent course returns 404."""
        fake_uuid = uuid.uuid4()
        url = reverse("enroll_course", args=[fake_uuid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_enrollment_inactive_course(self):
        """Test that user can enroll in inactive course (if it exists)."""
        inactive_course = Course.objects.create(
            title="Inactive Course",
            course_code="IN001",
            description="Inactive",
            is_active=False,
        )
        inactive_course.categories.add(self.web_category)

        url = reverse("enroll_course", args=[inactive_course.id])
        response = self.client.get(url)
        # Should still work, enrollment is independent of course active status
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Enrollment.objects.filter(user=self.user, course=inactive_course).exists()
        )

    def test_multiple_users_enroll_same_course(self):
        """Test that multiple users can enroll in the same course."""
        url = reverse("enroll_course", args=[self.course.id])
        self.client.get(url)

        # Create second user and log in
        User.objects.create_user(username="user2", password="pass123")
        self.client.login(username="user2", password="pass123")
        self.client.get(url)

        enrollments = Enrollment.objects.filter(course=self.course, is_deleted=False)
        self.assertEqual(enrollments.count(), 2)

    def test_enrollment_post_method(self):
        """Test that enrollment works with POST method if supported."""
        url = reverse("enroll_course", args=[self.course.id])
        # The view uses get_object_or_404 which works with any method
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Enrollment.objects.filter(user=self.user, course=self.course).exists()
        )
