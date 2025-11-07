# accounts/tests/test_models.py
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


class UserModelTestCase(TestCase):
    def setUp(self):
        self.user_data = {
            "username": "student1",
            "email": "student1@example.com",
            "password": "password123",
            "first_name": "John",
            "last_name": "Doe",
        }

    def test_user_creation_defaults_and_fields(self):
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, "student1")
        self.assertEqual(user.email, "student1@example.com")
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        # Django AbstractUser default
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        # UUID primary key
        self.assertIsInstance(user.id, uuid.UUID)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass",
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_active)
        self.assertIsInstance(admin.id, uuid.UUID)

    def test_unique_username_raises_integrity_error(self):
        User.objects.create_user(**self.user_data)
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username="student1",
                email="other@example.com",
                password="pass",
            )

    def test_duplicate_email_allowed_by_model(self):
        # If model allows duplicate emails, creating second user should succeed
        User.objects.create_user(**self.user_data)
        user2 = User.objects.create_user(
            username="student2",
            email="student1@example.com",
            password="pass",
        )
        self.assertEqual(user2.email, "student1@example.com")

    def test_password_is_hashed(self):
        user = User.objects.create_user(**self.user_data)
        self.assertNotEqual(user.password, "password123")
        self.assertTrue(user.check_password("password123"))

    def test_str_returns_username(self):
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), "student1")
