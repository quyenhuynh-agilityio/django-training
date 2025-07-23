from django.test import TestCase
from django.utils import timezone
import datetime
from polls.models import Question, Choice


class QuestionModelTests(TestCase):
    def setUp(self):
        # Setup run before each test
        self.question = Question.objects.create(
            question_text="What's your favorite color?", pub_date=timezone.now()
        )

    def test_was_published_recently_with_future_question(self):
        """was_published_recently() returns False for questions with future pub_date."""
        future_time = timezone.now() + datetime.timedelta(days=30)
        future_question = Question(
            question_text="Future question", pub_date=future_time
        )
        self.assertFalse(future_question.was_published_recently())

    def test_was_published_recently_with_old_question(self):
        """was_published_recently() returns False for questions older than 1 day."""
        old_time = timezone.now() - datetime.timedelta(days=2)
        old_question = Question(question_text="Old question", pub_date=old_time)
        self.assertFalse(old_question.was_published_recently())

    def test_was_published_recently_with_recent_question(self):
        """was_published_recently() returns True for questions within the last day."""
        recent_time = timezone.now() - datetime.timedelta(hours=12)
        recent_question = Question(
            question_text="Recent question", pub_date=recent_time
        )
        self.assertTrue(recent_question.was_published_recently())


class ChoiceModelTests(TestCase):
    def setUp(self):
        # Setup run before each test
        self.question = Question.objects.create(
            question_text="What's your favorite color?", pub_date=timezone.now()
        )
        self.choice = Choice.objects.create(
            question=self.question, choice_text="Blue", votes=0
        )

    def test_choice_string_representation(self):
        """Choice __str__ returns the choice_text."""
        self.assertEqual(str(self.choice), "Blue")

    def test_choice_question_relationship(self):
        """Choice is correctly linked to its Question."""
        self.assertEqual(self.choice.question, self.question)

    def test_choice_default_votes(self):
        """Choice votes default to 0."""
        self.assertEqual(self.choice.votes, 0)
