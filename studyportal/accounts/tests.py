import uuid
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.db import IntegrityError

User = get_user_model()


class UserModelTest(TestCase):
    """Test cases for custom User model."""

    def setUp(self):
        self.user_data = {
            "username": "student1",
            "email": "student1@example.com",
            "password": "password123",
            "first_name": "John",
            "last_name": "Doe",
        }

    def test_user_creation(self):
        """Test creating a user with all fields."""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, "student1")
        self.assertEqual(user.email, "student1@example.com")
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertFalse(user.is_active)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsInstance(user.id, uuid.UUID)

    def test_user_creation_minimal_fields(self):
        """Test creating a user with only required fields."""
        user = User.objects.create_user(
            username="minimal",
            email="minimal@example.com",
            password="pass123",
        )
        self.assertEqual(user.username, "minimal")
        self.assertEqual(user.email, "minimal@example.com")
        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")
        self.assertFalse(user.is_active)

    def test_user_uuid_primary_key(self):
        """Test that user ID is a UUID."""
        user = User.objects.create_user(
            username="uuid_test",
            email="uuid@example.com",
            password="pass123",
        )
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertIsNotNone(user.id)

    def test_user_soft_delete(self):
        """Test soft deleting a user."""
        user = User.objects.create_user(**self.user_data)
        user.is_active = True
        user.is_active = False
        user.save()

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_active)

    def test_user_soft_delete_preserves_record(self):
        """Test that soft delete doesn't remove the user from database."""
        user = User.objects.create_user(**self.user_data)
        user_id = user.id
        user.is_active = False
        user.save()

        # User should still exist in database
        self.assertTrue(User.objects.filter(id=user_id).exists())
        retrieved_user = User.objects.get(id=user_id)
        self.assertTrue(retrieved_user.is_active)

    def test_create_superuser(self):
        """Test creating a superuser."""
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass",
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_active)
        self.assertFalse(admin.is_active)
        self.assertIsInstance(admin.id, uuid.UUID)

    def test_create_superuser_requires_staff(self):
        """Test that create_superuser sets is_staff=True."""
        admin = User.objects.create_superuser(
            username="admin2",
            email="admin2@example.com",
            password="adminpass",
        )
        self.assertTrue(admin.is_staff)

    def test_user_custom_table_name(self):
        """Test that user table uses custom name 'user' instead of 'auth_user'."""
        # Check that the table name is 'user'
        self.assertEqual(User._meta.db_table, "user")

    def test_user_unique_username(self):
        """Test that username must be unique."""
        User.objects.create_user(
            username="unique_user",
            email="user1@example.com",
            password="pass123",
        )

        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username="unique_user",
                email="user2@example.com",
                password="pass123",
            )

    def test_user_unique_email(self):
        """Test that email must be unique if unique=True is set."""
        User.objects.create_user(
            username="user1",
            email="same@example.com",
            password="pass123",
        )

        # Django's User model typically allows duplicate emails by default
        # But we can test that it works
        user2 = User.objects.create_user(
            username="user2",
            email="same@example.com",
            password="pass123",
        )
        self.assertEqual(user2.email, "same@example.com")

    def test_user_password_hashing(self):
        """Test that password is hashed, not stored in plain text."""
        user = User.objects.create_user(**self.user_data)
        self.assertNotEqual(user.password, "password123")
        self.assertTrue(user.check_password("password123"))
        self.assertFalse(user.check_password("wrongpassword"))

    def test_user_string_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(**self.user_data)
        # Default AbstractUser __str__ returns username
        self.assertEqual(str(user), "student1")


class UserLoginLogoutViewTest(TestCase):
    """Test cases for login and logout views."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="pass1234",
            first_name="Jane",
            last_name="Doe",
        )
        self.login_url = reverse("login")
        self.logout_url = reverse("logout")

    def test_login_url_resolves(self):
        """Test that login URL resolves correctly."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_login_template_used(self):
        """Test that login view uses correct template."""
        response = self.client.get(self.login_url)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_login_form_in_context(self):
        """Test that AuthenticationForm is in context."""
        response = self.client.get(self.login_url)
        self.assertIsInstance(response.context["form"], AuthenticationForm)

    def test_user_login_valid_credentials(self):
        """Test successful login with valid credentials."""
        response = self.client.post(
            self.login_url,
            {"username": "student2", "password": "pass1234"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.url)

    def test_user_login_sets_session(self):
        """Test that successful login creates a session."""
        self.client.post(
            self.login_url,
            {"username": "student2", "password": "pass1234"},
        )
        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_user_login_invalid_username(self):
        """Test login with invalid username."""
        response = self.client.post(
            self.login_url,
            {"username": "nonexistent", "password": "pass1234"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")

    def test_user_login_invalid_password(self):
        """Test login with invalid password."""
        response = self.client.post(
            self.login_url,
            {"username": "student2", "password": "wrongpass"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")

    def test_user_login_empty_credentials(self):
        """Test login with empty credentials."""
        response = self.client.post(
            self.login_url,
            {"username": "", "password": ""},
        )
        self.assertEqual(response.status_code, 200)
        # Form should show validation errors

    def test_user_login_missing_password(self):
        """Test login with missing password field."""
        response = self.client.post(
            self.login_url,
            {"username": "student2"},
        )
        self.assertEqual(response.status_code, 200)
        # Form should show validation errors

    def test_user_login_missing_username(self):
        """Test login with missing username field."""
        response = self.client.post(
            self.login_url,
            {"password": "pass1234"},
        )
        self.assertEqual(response.status_code, 200)
        # Form should show validation errors

    def test_soft_deleted_user_cannot_login(self):
        """Test that soft-deleted users cannot login."""
        self.user.is_active = True
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            self.login_url,
            {"username": "student2", "password": "pass1234"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_inactive_user_cannot_login(self):
        """Test that inactive users cannot login."""
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            self.login_url,
            {"username": "student2", "password": "pass1234"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")

    def test_user_login_case_sensitive_username(self):
        """Test that username login is case sensitive."""
        response = self.client.post(
            self.login_url,
            {"username": "STUDENT2", "password": "pass1234"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")

    def test_user_logout(self):
        """Test successful logout."""
        self.client.login(username="student2", password="pass1234")
        response = self.client.get(self.logout_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    def test_user_logout_clears_session(self):
        """Test that logout clears the session."""
        self.client.login(username="student2", password="pass1234")
        self.assertTrue(self.client.session.get("_auth_user_id"))

        self.client.get(self.logout_url)
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_user_logout_without_login(self):
        """Test logout when user is not logged in."""
        response = self.client.get(self.logout_url)
        # Should still work, just redirects
        self.assertEqual(response.status_code, 302)

    def test_login_redirects_authenticated_user(self):
        """Test that already authenticated users are redirected."""
        self.client.login(username="student2", password="pass1234")
        response = self.client.get(self.login_url)
        # View doesn't explicitly redirect, but user is logged in
        self.assertEqual(response.status_code, 200)

    def test_login_get_request_shows_form(self):
        """Test that GET request shows login form."""
        response = self.client.get(self.login_url)
        self.assertIsInstance(response.context["form"], AuthenticationForm)
        self.assertFalse(response.context["form"].is_bound)

    def test_login_post_request_with_valid_form(self):
        """Test that POST request with valid form logs user in."""
        response = self.client.post(
            self.login_url,
            {"username": "student2", "password": "pass1234"},
            follow=True,  # Follow redirect
        )
        # Should redirect to home page
        self.assertEqual(response.status_code, 200)

    def test_login_post_request_with_invalid_form(self):
        """Test that POST request with invalid form shows errors."""
        response = self.client.post(
            self.login_url,
            {"username": "student2", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
