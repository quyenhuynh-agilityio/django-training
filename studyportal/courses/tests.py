from django.test import TestCase
from .models import Course


class CourseModelTest(TestCase):
    def setUp(self):
        self.course = Course.objects.create(
            title="Django Basics",
            description="Learn Django",
            category="Web Development",
        )

    def test_course_creation(self):
        self.assertEqual(self.course.title, "Django Basics")
        self.assertFalse(self.course.is_deleted)

    def test_soft_delete_course(self):
        self.course.is_deleted = True
        self.course.is_active = False
        self.course.save()
        course = Course.objects.get(title="Django Basics")
        self.assertTrue(course.is_deleted)
        self.assertFalse(course.is_active)
