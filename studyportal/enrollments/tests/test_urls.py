# enrollments/tests/test_urls.py
from django.test import TestCase


class EnrollmentsURLsTestCase(TestCase):
    """Test cases for enrollments URL patterns."""

    def test_enrollments_urls_empty(self):
        """Test that enrollments URLs are empty (no custom URLs defined)."""
        # enrollments/urls.py is empty, so no URLs to test
        # This test ensures the URL configuration doesn't break
        from enrollments import urls

        self.assertEqual(len(urls.urlpatterns), 0)
