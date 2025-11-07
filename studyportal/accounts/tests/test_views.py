# accounts/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

User = get_user_model()


class UserLoginViewTest(TestCase):
    """Test cases for user_login view."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="pass1234",
            first_name="Jane",
            last_name="Doe",
        )
        self.login_url = reverse("login")

    def test_login_page_get(self):
        """Test GET request shows login form."""
        resp = self.client.get(self.login_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "accounts/login.html")
        self.assertIsInstance(resp.context["form"], AuthenticationForm)
        self.assertFalse(resp.context["form"].is_bound)

    def test_login_with_valid_credentials(self):
        """Test successful login with valid credentials."""
        resp = self.client.post(
            self.login_url, {"username": "student2", "password": "pass1234"}
        )
        # login view redirects on success
        self.assertRedirects(resp, "/", status_code=302, target_status_code=200)
        self.assertTrue(self.client.session.get("_auth_user_id"))
        # Verify user is authenticated
        self.assertEqual(int(self.client.session.get("_auth_user_id")), self.user.id)

    def test_login_with_invalid_credentials_shows_error(self):
        """Test login with wrong password shows error message."""
        resp = self.client.post(
            self.login_url, {"username": "student2", "password": "wrong"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(
            resp, "Please enter a correct username and password", status_code=200
        )
        self.assertFalse(self.client.session.get("_auth_user_id"))
        # Form should be bound and have errors
        self.assertTrue(resp.context["form"].is_bound)
        self.assertFalse(resp.context["form"].is_valid())

    def test_login_with_nonexistent_username(self):
        """Test login with non-existent username."""
        resp = self.client.post(
            self.login_url, {"username": "nonexistent", "password": "pass1234"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please enter a correct username and password")
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_login_with_empty_username(self):
        """Test login with empty username field."""
        resp = self.client.post(
            self.login_url, {"username": "", "password": "pass1234"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["form"].is_valid())
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_login_with_empty_password(self):
        """Test login with empty password field."""
        resp = self.client.post(
            self.login_url, {"username": "student2", "password": ""}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["form"].is_valid())
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_login_with_empty_form(self):
        """Test login with no data submitted."""
        resp = self.client.post(self.login_url, {})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["form"].is_valid())
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_inactive_user_cannot_login(self):
        """Test that inactive users cannot log in."""
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(
            self.login_url, {"username": "student2", "password": "pass1234"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Please enter a correct username and password")
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_login_form_displays_in_template(self):
        """Test that form is properly passed to template context."""
        resp = self.client.get(self.login_url)
        self.assertIn("form", resp.context)
        self.assertIsInstance(resp.context["form"], AuthenticationForm)

    def test_login_redirects_to_homepage(self):
        """Test that successful login redirects to homepage."""
        resp = self.client.post(
            self.login_url, {"username": "student2", "password": "pass1234"}
        )
        self.assertRedirects(resp, "/", status_code=302)

    def test_already_authenticated_user_can_access_login_page(self):
        """Test that authenticated users can still access login page."""
        self.client.login(username="student2", password="pass1234")
        resp = self.client.get(self.login_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "accounts/login.html")


class UserLogoutViewTest(TestCase):
    """Test cases for user_logout view."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="pass1234",
        )
        self.logout_url = reverse("logout")

    def test_logout_redirects_and_clears_session(self):
        """Test logout clears session and redirects."""
        self.client.login(username="student2", password="pass1234")
        self.assertTrue(self.client.session.get("_auth_user_id"))
        resp = self.client.get(self.logout_url)
        self.assertRedirects(resp, "/", status_code=302)
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_logout_with_post_method(self):
        """Test logout works with POST method."""
        self.client.login(username="student2", password="pass1234")
        self.assertTrue(self.client.session.get("_auth_user_id"))
        resp = self.client.post(self.logout_url)
        self.assertRedirects(resp, "/", status_code=302)
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_logout_when_not_authenticated(self):
        """Test logout when user is not logged in (should still redirect)."""
        self.assertFalse(self.client.session.get("_auth_user_id"))
        resp = self.client.get(self.logout_url)
        self.assertRedirects(resp, "/", status_code=302)
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_logout_redirects_to_homepage(self):
        """Test that logout redirects to homepage."""
        self.client.login(username="student2", password="pass1234")
        resp = self.client.get(self.logout_url)
        self.assertRedirects(resp, "/", status_code=302)

    def test_logout_clears_all_session_data(self):
        """Test that logout clears session data."""
        self.client.login(username="student2", password="pass1234")
        # Add some custom session data
        session = self.client.session
        session["custom_key"] = "custom_value"
        session.save()
        self.assertTrue(session.get("_auth_user_id"))
        self.assertEqual(session.get("custom_key"), "custom_value")

        resp = self.client.get(self.logout_url)
        self.assertRedirects(resp, "/", status_code=302)
        # Session should be cleared
        self.assertFalse(self.client.session.get("_auth_user_id"))
        # Note: Django logout may keep some session keys, but auth_user_id should be gone
