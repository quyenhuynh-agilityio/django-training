from django.test import TestCase
from django.contrib.auth import get_user_model
from courses.models import Course
from .models import Enrollment

User = get_user_model()


class EnrollmentTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student1", password="password")
        self.course = Course.objects.create(
            title="Django", description="Learn Django", category="Web"
        )
        self.enrollment = Enrollment.objects.create(user=self.user, course=self.course)

    def test_enrollment_creation(self):
        self.assertEqual(self.enrollment.user.username, "student1")
        self.assertEqual(self.enrollment.course.title, "Django")
        self.assertFalse(self.enrollment.is_deleted)

    def test_soft_delete_enrollment(self):
        self.enrollment.is_deleted = True
        self.enrollment.save()
        enrollment = Enrollment.objects.get(pk=self.enrollment.pk)
        self.assertTrue(enrollment.is_deleted)
