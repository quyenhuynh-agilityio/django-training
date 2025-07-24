from django.test import TestCase
from django.urls import reverse, resolve
from polls.views import index, detail, results, vote


class PollsURLsTest(TestCase):
    def test_index_url(self):
        """Test that the root URL resolves to the index view."""
        url = reverse("index")
        self.assertEqual(url, "/")
        resolver = resolve("/")
        self.assertEqual(resolver.func, index)
        self.assertEqual(resolver.view_name, "index")

    def test_detail_url(self):
        """Test that the detail URL resolves to the detail view."""
        url = reverse("detail", args=[5])
        self.assertEqual(url, "/5/")
        resolver = resolve("/5/")
        self.assertEqual(resolver.func, detail)
        self.assertEqual(resolver.view_name, "detail")
        self.assertEqual(resolver.kwargs, {"question_id": 5})

    def test_results_url(self):
        """Test that the results URL resolves to the results view."""
        url = reverse("results", args=[5])
        self.assertEqual(url, "/5/results/")
        resolver = resolve("/5/results/")
        self.assertEqual(resolver.func, results)
        self.assertEqual(resolver.view_name, "results")
        self.assertEqual(resolver.kwargs, {"question_id": 5})

    def test_vote_url(self):
        """Test that the vote URL resolves to the vote view."""
        url = reverse("vote", args=[5])
        self.assertEqual(url, "/5/vote/")
        resolver = resolve("/5/vote/")
        self.assertEqual(resolver.func, vote)
        self.assertEqual(resolver.view_name, "vote")
        self.assertEqual(resolver.kwargs, {"question_id": 5})

    def test_debug_toolbar_urls(self):
        """Test that debug toolbar URLs are included and resolve correctly."""
        url = reverse("djdt:render_panel")
        self.assertTrue(url.startswith("/__debug__/"))
        resolver = resolve(url)
        self.assertEqual(resolver.namespace, "djdt")
        self.assertEqual(resolver.view_name, "djdt:render_panel")
