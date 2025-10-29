from django.test import TestCase
from django.contrib.auth import get_user_model


# Create your tests here.
User = get_user_model()


class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="password123",
            first_name="John",
            last_name="Doe",
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, "student1")
        self.assertFalse(self.user.is_deleted)

    def test_soft_delete_user(self):
        self.user.is_deleted = True
        self.user.is_active = False
        self.user.save()
        user = User.objects.get(username="student1")
        self.assertTrue(user.is_deleted)
        self.assertFalse(user.is_active)
