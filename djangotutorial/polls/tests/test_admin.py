from django.contrib import admin
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from polls.models import Question, Choice
from polls.admin import ChoiceInline, QuestionAdmin, CustomAdminSite


class ChoiceInlineTest(TestCase):
    def setUp(self):
        self.admin_site = admin.site
        self.question = Question.objects.create(
            question_text="Test question", pub_date=timezone.now()
        )

    def test_choice_inline_model(self):
        """Test that ChoiceInline uses the correct model."""
        inline = ChoiceInline(Choice, self.admin_site)
        self.assertEqual(inline.model, Choice)

    def test_choice_inline_extra(self):
        """Test that ChoiceInline has the correct number of extra forms."""
        inline = ChoiceInline(Choice, self.admin_site)
        self.assertEqual(inline.extra, 3)


class QuestionAdminTest(TestCase):
    def setUp(self):
        self.admin_site = admin.site
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client.login(username="admin", password="password")
        self.question = Question.objects.create(
            question_text="Test question", pub_date=timezone.now()
        )

    def test_question_admin_fieldsets(self):
        """Test that QuestionAdmin has the correct fieldsets configuration."""
        question_admin = QuestionAdmin(Question, self.admin_site)
        expected_fieldsets = [
            (None, {"fields": ["question_text"]}),
            ("Date information", {"fields": ["pub_date"], "classes": ["collapse"]}),
        ]
        self.assertEqual(question_admin.fieldsets, expected_fieldsets)

    def test_question_admin_inlines(self):
        """Test that QuestionAdmin includes ChoiceInline."""
        question_admin = QuestionAdmin(Question, self.admin_site)
        self.assertEqual(question_admin.inlines, [ChoiceInline])

    def test_question_admin_list_display(self):
        """Test that QuestionAdmin has the correct list_display configuration."""
        question_admin = QuestionAdmin(Question, self.admin_site)
        expected_list_display = ["question_text", "pub_date", "was_published_recently"]
        self.assertEqual(question_admin.list_display, expected_list_display)

    def test_question_admin_list_filter(self):
        """Test that QuestionAdmin has the correct list_filter configuration."""
        question_admin = QuestionAdmin(Question, self.admin_site)
        self.assertEqual(question_admin.list_filter, ["pub_date"])

    def test_question_admin_search_fields(self):
        """Test that QuestionAdmin has the correct search_fields configuration."""
        question_admin = QuestionAdmin(Question, self.admin_site)
        self.assertEqual(question_admin.search_fields, ["question_text"])

    def test_question_admin_list_per_page(self):
        """Test that QuestionAdmin has the correct list_per_page configuration."""
        question_admin = QuestionAdmin(Question, self.admin_site)
        self.assertEqual(question_admin.list_per_page, 1)

    def test_question_admin_change_list_pagination(self):
        """Test that the question admin change list paginates correctly."""
        # Create multiple questions to test pagination
        for i in range(3):
            Question.objects.create(
                question_text=f"Question {i}", pub_date=timezone.now()
            )
        response = self.client.get(reverse("custom_admin:polls_question_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["cl"].result_list), 1)  # Only 1 per page

    def test_question_admin_search(self):
        """Test that the search functionality works in the question admin."""
        response = self.client.get(
            reverse("custom_admin:polls_question_changelist"), {"q": "Test"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test question")

    def test_question_admin_list_filter(self):
        """Test that the list filter for pub_date is present."""
        response = self.client.get(reverse("custom_admin:polls_question_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("pub_date", response.content.decode())


class CustomAdminSiteTest(TestCase):
    def setUp(self):
        self.admin_site = CustomAdminSite(name="custom_admin")
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client.login(username="admin", password="password")

    def test_custom_admin_site_header(self):
        """Test that CustomAdminSite has the correct site_header."""
        self.assertEqual(self.admin_site.site_header, "Polls Administration")

    def test_custom_admin_site_registration(self):
        """Test that Question model is registered with QuestionAdmin."""
        registered_model_admins = self.admin_site._registry
        self.assertIn(Question, registered_model_admins)
        self.assertIsInstance(registered_model_admins[Question], QuestionAdmin)

    def test_custom_admin_site_index(self):
        """Test that the custom admin site index page loads correctly."""
        response = self.client.get(reverse("custom_admin:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Polls Administration")
