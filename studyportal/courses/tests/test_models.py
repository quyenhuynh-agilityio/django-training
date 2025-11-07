# courses/tests/test_models.py
import uuid
from django.test import TestCase
from courses.models import Course, Category

User = None  # Not needed for model tests


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
        self.assertIsInstance(course.id, uuid.UUID)

    def test_course_creation_minimal_fields(self):
        """Test creating a course with only required fields."""
        programming_category = Category.objects.create(
            name="Programming", is_active=True
        )
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

    def test_course_soft_delete(self):
        """Test soft deleting a course."""
        course = Course.objects.create(**self.course_data)
        self.assertTrue(course.is_active)

        course.is_active = False
        course.save()

        course.refresh_from_db()
        self.assertFalse(course.is_active)

    def test_course_string_representation(self):
        """Test course __str__ method."""
        course = Course.objects.create(**self.course_data)
        self.assertEqual(str(course), "Django Basics")

    def test_course_ordering(self):
        """Test that courses are ordered by title."""
        test_category = Category.objects.create(name="Test", is_active=True)
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
        category = Category.objects.create(name="Web Development", is_active=True)
        course1 = Course.objects.create(
            title="Django Basics",
            course_code="DJ101",
            description="Learn Django",
            is_active=True,
        )
        course1.categories.add(category)
        course2 = Course.objects.create(
            title="React Basics",
            course_code="RE101",
            description="Learn React",
            is_active=True,
        )
        course2.categories.add(category)

        self.assertEqual(category.courses.count(), 2)
        self.assertIn(course1, category.courses.all())
        self.assertIn(course2, category.courses.all())

    def test_category_removed_on_delete(self):
        """Test that courses' categories are removed when category is deleted."""
        category = Category.objects.create(name="Web Development", is_active=True)
        course = Course.objects.create(
            title="Django Basics",
            course_code="DJ101",
            description="Learn Django",
            is_active=True,
        )
        course.categories.add(category)

        category.delete()

        course.refresh_from_db()
        self.assertEqual(course.categories.count(), 0)
        self.assertNotIn(category, course.categories.all())
