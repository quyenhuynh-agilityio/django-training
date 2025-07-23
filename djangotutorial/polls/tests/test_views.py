from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from polls.models import Question, Choice
import datetime


class PollsViewTests(TestCase):
    def setUp(self):
        # Initialize test client and create test data
        self.client = Client()
        # Create two questions for testing
        self.question1 = Question.objects.create(
            question_text="What's your favorite color?",
            pub_date=timezone.now() - datetime.timedelta(days=1),
        )
        self.question2 = Question.objects.create(
            question_text="What's your favorite food?", pub_date=timezone.now()
        )
        self.choice1 = Choice.objects.create(
            question=self.question1, choice_text="Blue", votes=0
        )

    def test_index_view_with_questions(self):
        """Index view should display recent questions in the correct order."""
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "polls/index.html")
        # Check that questions are ordered by pub_date (newest first)
        self.assertQuerysetEqual(
            response.context["latest_question_list"],
            [self.question2, self.question1],
            transform=lambda x: x,  # Convert queryset to list for comparison
        )
        self.assertContains(response, "What's your favorite food?")
        self.assertContains(response, "What's your favorite color?")

    def test_index_view_with_no_questions(self):
        """Index view should handle case with no questions."""
        Question.objects.all().delete()  # Clear all questions
        response = self.client.get(reverse("polls:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "polls/index.html")
        self.assertQuerysetEqual(response.context["latest_question_list"], [])
        self.assertContains(response, "No polls are available.")

    def test_detail_view_with_valid_question(self):
        """Detail view should display the question's details."""
        response = self.client.get(reverse("polls:detail", args=(self.question1.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "polls/detail.html")
        self.assertEqual(response.context["question"], self.question1)
        self.assertContains(response, self.question1.question_text)
        self.assertContains(response, self.choice1.choice_text)

    def test_detail_view_with_invalid_question(self):
        """Detail view should return 404 for non-existent question."""
        response = self.client.get(reverse("polls:detail", args=(999,)))
        self.assertEqual(response.status_code, 404)

    def test_results_view(self):
        """Results view should return correct response for a question."""
        response = self.client.get(reverse("polls:results", args=(self.question1.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, f"You're looking at the results of question {self.question1.id}."
        )

    def test_vote_view(self):
        """Vote view should return correct response for a question."""
        response = self.client.get(reverse("polls:vote", args=(self.question1.id,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"You're voting on question {self.question1.id}")
