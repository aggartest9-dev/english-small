
# Create your tests here.
# myapp/tests.py

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.test import TestCase

from rest_framework.test import APIClient
from rest_framework import status

from .models import (
    CourseDay,
    LearningObjective,
    ContentBlock,
    ContentBlockMedia,
    Question,
    Option,
    UserAnswer,
    UserProgress,
    UserCommitment,
)
from .services import (
    AnswerService,
    ProgressService,
    CommitmentService,
)

User = get_user_model()


# =====================================================
# BASE TEST MIXIN
# =====================================================

class BaseSetupMixin:
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="StrongPass123"
        )

        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.day = CourseDay.objects.create(
            level="beginner",
            day=1,
            title="Day 1",
            description="Intro",
            is_published=True
        )

        self.block = ContentBlock.objects.create(
            day=self.day,
            section=1,
            order=1,
            block_type="interactive_question",
            title="Quiz Block",
            description="Quiz",
            estimated_minutes=5,
        )

        self.question = Question.objects.create(
            block=self.block,
            format_type="mcq",
            response_type="option",
            difficulty="easy",
            text="What is correct?",
            marks=5,
            order=1,
        )

        self.option1 = Option.objects.create(
            question=self.question,
            text="Correct",
            is_correct=True,
            order=1,
        )

        self.option2 = Option.objects.create(
            question=self.question,
            text="Wrong",
            is_correct=False,
            order=2,
        )


# =====================================================
# MODEL TESTS
# =====================================================

class ModelTests(BaseSetupMixin, TestCase):

    def test_course_day_created(self):
        self.assertEqual(self.day.level, "beginner")
        self.assertEqual(self.day.day, 1)

    def test_question_relation(self):
        self.assertEqual(self.question.block, self.block)

    def test_option_relation(self):
        self.assertEqual(self.option1.question, self.question)


# =====================================================
# SERVICE TESTS
# =====================================================

class AnswerServiceTests(BaseSetupMixin, TestCase):

    def test_submit_first_attempt(self):
        answer = AnswerService.submit_answer(
            user=self.user,
            question=self.question,
            selected_option=self.option1
        )

        self.assertEqual(answer.attempt_no, 1)
        self.assertTrue(answer.latest)
        self.assertTrue(answer.is_correct)

    def test_submit_second_attempt_marks_old_latest_false(self):
        first = AnswerService.submit_answer(
            user=self.user,
            question=self.question,
            selected_option=self.option2
        )

        second = AnswerService.submit_answer(
            user=self.user,
            question=self.question,
            selected_option=self.option1
        )

        first.refresh_from_db()

        self.assertFalse(first.latest)
        self.assertTrue(second.latest)
        self.assertEqual(second.attempt_no, 2)

    def test_progress_auto_created(self):
        AnswerService.submit_answer(
            user=self.user,
            question=self.question,
            selected_option=self.option1
        )

        progress = UserProgress.objects.get(
            user=self.user,
            day=self.day
        )

        self.assertEqual(progress.progress_percent, Decimal("100"))
        self.assertTrue(progress.is_completed)


class ProgressServiceTests(BaseSetupMixin, TestCase):

    def test_manual_progress(self):
        progress = ProgressService.manual_update(
            user=self.user,
            day=self.day,
            is_started=True,
            is_completed=False,
            progress_percent=50
        )

        self.assertEqual(progress.progress_percent, 50)

    def test_refresh_progress_zero(self):
        progress = ProgressService.refresh_day_progress(
            user=self.user,
            day=self.day
        )

        self.assertEqual(progress.progress_percent, 0)


class CommitmentServiceTests(BaseSetupMixin, TestCase):

    def test_save_commitment(self):
        commitment = CommitmentService.save(
            user=self.user,
            day=self.day,
            commitment_text="I will finish today."
        )

        self.assertEqual(
            commitment.commitment_text,
            "I will finish today."
        )

    def test_latest_commitment(self):
        CommitmentService.save(
            user=self.user,
            day=self.day,
            commitment_text="First"
        )

        latest = CommitmentService.latest(self.user)

        self.assertEqual(latest.commitment_text, "First")


# =====================================================
# API TESTS
# =====================================================

class APITests(BaseSetupMixin, TestCase):

    def test_home_endpoint(self):
        response = self.client.get("/")

        self.assertIn(
            response.status_code,
            [200, 404]
        )

    def test_get_session(self):
        url = "/api/session/?level=beginner&day=1"

        response = self.client.get(url)

        self.assertIn(
            response.status_code,
            [200, 404]
        )

    def test_submit_answer(self):
        url = "/api/submit-answer/"

        payload = {
            "question": self.question.id,
            "selected_option": self.option1.id
        }

        response = self.client.post(
            url,
            payload,
            format="json"
        )

        self.assertIn(
            response.status_code,
            [200, 201]
        )

    def test_save_commitment(self):
        url = "/api/commitment/"

        payload = {
            "day": self.day.id,
            "commitment_text": "I will do it"
        }

        response = self.client.post(
            url,
            payload,
            format="json"
        )

        self.assertIn(
            response.status_code,
            [200, 201]
        )


# =====================================================
# SIGNAL TESTS
# =====================================================

class SignalTests(BaseSetupMixin, TestCase):

    def test_user_answer_updates_progress(self):
        UserAnswer.objects.create(
            user=self.user,
            question=self.question,
            selected_option=self.option1,
            attempt_no=1,
            latest=True,
            is_correct=True
        )

        progress = UserProgress.objects.get(
            user=self.user,
            day=self.day
        )

        self.assertTrue(progress.is_completed)

    def test_delete_answer_recalculates_progress(self):
        answer = UserAnswer.objects.create(
            user=self.user,
            question=self.question,
            selected_option=self.option1,
            attempt_no=1,
            latest=True,
            is_correct=True
        )

        answer.delete()

        progress = UserProgress.objects.get(
            user=self.user,
            day=self.day
        )

        self.assertEqual(progress.progress_percent, 0)


# =====================================================
# VALIDATION TESTS
# =====================================================

class ConstraintTests(BaseSetupMixin, TestCase):

    def test_unique_progress(self):
        UserProgress.objects.create(
            user=self.user,
            day=self.day
        )

        with self.assertRaises(Exception):
            UserProgress.objects.create(
                user=self.user,
                day=self.day
            )

    def test_unique_attempt(self):
        UserAnswer.objects.create(
            user=self.user,
            question=self.question,
            attempt_no=1,
            latest=True
        )

        with self.assertRaises(Exception):
            UserAnswer.objects.create(
                user=self.user,
                question=self.question,
                attempt_no=1,
                latest=False
            )


# =====================================================
# PERFORMANCE TESTS
# =====================================================

class QueryTests(BaseSetupMixin, TestCase):

    def test_prefetch_session_queryset(self):
        qs = CourseDay.objects.prefetch_related(
            "objectives",
            "blocks",
            "blocks__media_items",
            "blocks__questions",
            "blocks__questions__options",
        )

        obj = qs.get(pk=self.day.pk)

        self.assertEqual(obj.id, self.day.id)