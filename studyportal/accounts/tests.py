import uuid
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

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
        # UUID type check
        self.assertIsInstance(self.user.id, uuid.UUID)

    def test_soft_delete_user(self):
        self.user.is_deleted = True
        self.user.is_active = False
        self.user.save()

        user = User.objects.get(username="student1")
        self.assertTrue(user.is_deleted)
        self.assertFalse(user.is_active)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass"
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertIsInstance(admin.id, uuid.UUID)


class UserLoginLogoutViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="pass1234",
            first_name="Jane",
            last_name="Doe",
        )

    def test_login_url_resolves(self):
        url = reverse("login")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_user_login_valid_credentials(self):
        response = self.client.post(
            reverse("login"), {"username": "student2", "password": "pass1234"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.url)

    def test_user_login_invalid_credentials(self):
        response = self.client.post(
            reverse("login"),
            {"username": "student2", "password": "wrongpass"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_soft_deleted_user_cannot_login(self):
        self.user.is_deleted = True
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            reverse("login"), {"username": "student2", "password": "pass1234"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_user_logout(self):
        self.client.login(username="student2", password="pass1234")
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
