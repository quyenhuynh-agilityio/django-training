# accounts/tests/test_urls.py
from django.test import TestCase
from django.urls import reverse, resolve
from accounts.views import user_login, user_logout


class AccountsURLsTestCase(TestCase):
    """Test cases for accounts URL patterns."""

    def test_login_url_resolves(self):
        """Test that login URL resolves to correct view."""
        url = reverse("login")
        self.assertEqual(url, "/accounts/login/")
        resolved = resolve(url)
        self.assertEqual(resolved.func, user_login)

    def test_logout_url_resolves(self):
        """Test that logout URL resolves to correct view."""
        url = reverse("logout")
        self.assertEqual(url, "/accounts/logout/")
        resolved = resolve(url)
        self.assertEqual(resolved.func, user_logout)

    def test_login_url_accessible(self):
        """Test that login URL is accessible."""
        url = reverse("login")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_logout_url_accessible(self):
        """Test that logout URL is accessible."""
        url = reverse("logout")
        response = self.client.get(url)
        # Logout redirects even when not logged in
        self.assertIn(response.status_code, (200, 302))
