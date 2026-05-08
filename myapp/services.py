# myapp/services.py

from decimal import Decimal, ROUND_HALF_UP
import json
from openai import OpenAI
from django.conf import settings
from .models import UserAnswer, AIEvaluation, GradingStatusChoices
from django.db import transaction
from django.db.models import (
    Max,
    Sum,
    Count,
    Q,
)
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from .models import (
    CourseDay,
    ContentBlock,
    Question,
    UserAnswer,
    UserProgress,
    UserCommitment,
)

client = OpenAI(api_key=settings.OPENAI_API_KEY) 


# =====================================================
# CONSTANTS
# =====================================================

TWO_DP = Decimal("0.01")


# =====================================================
# SESSION SERVICE
# =====================================================

class SessionService:
    """
    Read-only business logic for course sessions.
    """

    @staticmethod
    def get_day(*, level: str, day: int):
        return (
            CourseDay.objects
            .prefetch_related(
                "objectives",
                "blocks",
                "blocks__media_items",
                "blocks__questions",
                "blocks__questions__options",
            )
            .get(
                level=level,
                day=day,
                is_published=True,
            )
        )

    @staticmethod
    def get_level_days(*, level: str):
        return (
            CourseDay.objects
            .filter(
                level=level,
                is_published=True,
            )
            .only(
                "id",
                "level",
                "day",
                "title",
                "description",
            )
            .order_by("day")
        )


# =====================================================
# ANSWER SERVICE
# =====================================================

class AnswerService:
    """
    Multi-attempt answer submission logic.
    """

    @staticmethod
    def _is_correct(question, selected_option):
        if question.response_type != "option":
            return False

        if not selected_option:
            return False

        return bool(selected_option.is_correct)

    @staticmethod
    def _next_attempt_locked(*, user, question):
        data = (
            UserAnswer.objects
            .select_for_update()
            .filter(
                user=user,
                question=question,
            )
            .aggregate(max_attempt=Max("attempt_no"))
        )

        return (data["max_attempt"] or 0) + 1

    @staticmethod
    @transaction.atomic
    def submit_answer(
        *,
        user,
        question,
        selected_option=None,
        text_answer="",
        audio_file=None,
        video_file=None,
    ):
        """
        Creates new attempt.
        Marks previous latest=False.
        Refreshes progress automatically.
        """

        existing = (
            UserAnswer.objects
            .select_for_update()
            .filter(
                user=user,
                question=question,
            )
        )

        existing.filter(latest=True).update(latest=False)

        attempt_no = AnswerService._next_attempt_locked(
            user=user,
            question=question,
        )

        answer = UserAnswer.objects.create(
            user=user,
            question=question,
            selected_option=selected_option,
            text_answer=text_answer or "",
            audio_file=audio_file,
            video_file=video_file,
            latest=True,
            attempt_no=attempt_no,
            is_correct=AnswerService._is_correct(
                question,
                selected_option,
            ),
        )

        ProgressService.refresh_day_progress(
            user=user,
            day=question.block.day,
        )

        return answer

    @staticmethod
    def user_question_history(*, user, question):
        return (
            UserAnswer.objects
            .filter(
                user=user,
                question=question,
            )
            .select_related(
                "question",
                "selected_option",
            )
            .order_by("-attempt_no")
        )


# =====================================================
# PROGRESS SERVICE
# =====================================================

class ProgressService:
    """
    Progress calculation engine.
    """

    @staticmethod
    def _required_questions_queryset(day):
        return Question.objects.filter(
            block__day=day,
            block__is_active=True,
            is_active=True,
            is_required=True,
        )

    @staticmethod
    def total_required_questions(day):
        return ProgressService._required_questions_queryset(day).count()

    @staticmethod
    def answered_required_questions(*, user, day):
        return (
            UserAnswer.objects
            .filter(
                user=user,
                latest=True,
                question__in=ProgressService._required_questions_queryset(day),
            )
            .values("question_id")
            .distinct()
            .count()
        )

    @staticmethod
    def score(*, user, day):
        data = (
            UserAnswer.objects
            .filter(
                user=user,
                latest=True,
                is_correct=True,
                question__block__day=day,
                question__block__is_active=True,
                question__is_active=True,
            )
            .aggregate(total=Sum("question__marks"))
        )

        return Decimal(data["total"] or 0)

    @staticmethod
    def calculate_percent(*, answered, total):
        if total <= 0:
            return Decimal("0.00")

        percent = (Decimal(answered) * Decimal("100")) / Decimal(total)

        return percent.quantize(
            TWO_DP,
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    @transaction.atomic
    def refresh_day_progress(*, user, day):
        total_required = ProgressService.total_required_questions(day)
        answered = ProgressService.answered_required_questions(
            user=user,
            day=day,
        )
        score = ProgressService.score(
            user=user,
            day=day,
        )

        percent = ProgressService.calculate_percent(
            answered=answered,
            total=total_required,
        )

        completed = (
            total_required > 0 and
            answered >= total_required
        )

        progress, _ = UserProgress.objects.update_or_create(
            user=user,
            day=day,
            defaults={
                "is_started": answered > 0,
                "is_completed": completed,
                "score": score,
                "progress_percent": percent,
                "completed_at": (
                    timezone.now()
                    if completed else None
                ),
            }
        )

        return progress

    @staticmethod
    @transaction.atomic
    def manual_update(
        *,
        user,
        day,
        is_started=True,
        is_completed=False,
    ):
        """
        Manual status update.
        Score recalculated safely.
        """

        score = ProgressService.score(
            user=user,
            day=day,
        )

        progress, _ = UserProgress.objects.update_or_create(
            user=user,
            day=day,
            defaults={
                "is_started": is_started,
                "is_completed": is_completed,
                "score": score,
                "completed_at": (
                    timezone.now()
                    if is_completed else None
                ),
            }
        )

        return progress

    @staticmethod
    def get_user_progress(*, user, day):
        return UserProgress.objects.filter(
            user=user,
            day=day,
        ).first()


# =====================================================
# COMMITMENT SERVICE
# =====================================================

class CommitmentService:
    """
    Commitment write/read helpers.
    """

    @staticmethod
    @transaction.atomic
    def save(
        *,
        user,
        day,
        commitment_text,
        is_completed=False,
    ):
        obj, _ = UserCommitment.objects.update_or_create(
            user=user,
            day=day,
            defaults={
                "commitment_text": commitment_text,
                "is_completed": is_completed,
            }
        )

        return obj

    @staticmethod
    def latest(*, user):
        return (
            UserCommitment.objects
            .filter(user=user)
            .select_related("day")
            .order_by("-updated_at", "-created_at")
            .first()
        )

    @staticmethod
    def user_commitments(*, user):
        return (
            UserCommitment.objects
            .filter(user=user)
            .select_related("day")
            .order_by("-updated_at")
        )


# =====================================================
# ANALYTICS SERVICE
# =====================================================

class AnalyticsService:
    """
    Reporting / admin stats.
    """

    @staticmethod
    def user_day_stats(*, user, day):
        attempts = UserAnswer.objects.filter(
            user=user,
            question__block__day=day,
        ).count()

        correct_latest = UserAnswer.objects.filter(
            user=user,
            latest=True,
            is_correct=True,
            question__block__day=day,
        ).count()

        progress = UserProgress.objects.filter(
            user=user,
            day=day,
        ).first()

        return {
            "attempts": attempts,
            "correct_latest_answers": correct_latest,
            "progress_percent": (
                progress.progress_percent
                if progress else Decimal("0.00")
            ),
            "score": (
                progress.score
                if progress else Decimal("0.00")
            ),
            "completed": (
                progress.is_completed
                if progress else False
            ),
        }

    @staticmethod
    def level_completion_rate(*, level):
        total = UserProgress.objects.filter(
            day__level=level,
        ).count()

        completed = UserProgress.objects.filter(
            day__level=level,
            is_completed=True,
        ).count()

        if total == 0:
            return Decimal("0.00")

        percent = (
            Decimal(completed) * Decimal("100")
        ) / Decimal(total)

        return percent.quantize(
            TWO_DP,
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def level_summary(*, level):
        return UserProgress.objects.filter(
            day__level=level
        ).aggregate(
            users_started=Count(
                "user",
                distinct=True,
                filter=Q(is_started=True),
            ),
            users_completed=Count(
                "user",
                distinct=True,
                filter=Q(is_completed=True),
            ),
            entries=Count("id"),
        )
    

class AIService:
    @staticmethod
    def transcribe_audio(file_path):
        """Uses OpenAI Whisper to turn audio/video into text."""
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcript.text
    @staticmethod
    def evaluate_answer(answer_id, use_mock=False):
        answer = UserAnswer.objects.select_related('question__block').get(id=answer_id)
        
        text_to_grade = answer.text_answer
        if (answer.audio_file or answer.video_file) and not text_to_grade:
            text_to_grade = AIService.transcribe_audio(answer.audio_file.path)

        if use_mock:
            return AIService._save_mock_eval(answer, text_to_grade)

        # UPDATED PROMPT WITH SENTIMENT AND CONFIDENCE
        prompt = f"""
        Analyze this English learner's response for a body language/confidence course.
        
        QUESTION: {answer.question.text}
        LESSON CONTEXT: {answer.question.block.description}
        USER RESPONSE: "{text_to_grade}"

        OUTPUT JSON STRUCTURE:
        {{
            "scores": {{
                "grammar": 1-5,
                "vocabulary": 1-5,
                "clarity": 1-5,
                "coherence": 1-5,
                "fluency": 1-5,
                "confidence": 1-5,
                "relevance": 1-5
            }},
            "analysis": {{
                "sentiment": "String (e.g. Positive, Nervous, Determined)",
                "estimated_level": "CEFR Level (A1-C2)",
                "filler_words_count": "Integer count of 'um', 'ah', 'like', 'you know'"
            }},
            "feedback": {{
                "errors": [{{ "type": "string", "example": "string", "severity": "minor/major" }}],
                "strengths": ["string"],
                "improvements": ["string"]
            }}
        }}
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional linguistic coach and psychologist."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )

        result = json.loads(response.choices[0].message.content)
        
        # Mapping JSON keys to Database Fields
        scores = result.get('scores', {})
        analysis = result.get('analysis', {})
        feedback = result.get('feedback', {})

        eval_obj, _ = AIEvaluation.objects.update_or_create(
            user_answer=answer,
            defaults={
                "transcription": text_to_grade,
                "grammar_score": scores.get('grammar'),
                "vocabulary_score": scores.get('vocabulary'),
                "clarity_score": scores.get('clarity'),
                "coherence_score": scores.get('coherence'),
                "fluency_score": scores.get('fluency'),
                "confidence_score": scores.get('confidence'),
                "relevance_score": scores.get('relevance'),
                "sentiment": analysis.get('sentiment'),
                "estimated_level": analysis.get('estimated_level'),
                "filler_words_count": analysis.get('filler_words_count', 0),
                "errors": feedback.get('errors', []),
                "strengths": feedback.get('strengths', []),
                "improvements": feedback.get('improvements', []),
            }
        )
        
        answer.grading_status = GradingStatusChoices.COMPLETE
        answer.save()
        return eval_obj

    @staticmethod
    def _save_mock_eval(answer, text):
        # Helper for your manual testing without spending API credits
        eval_obj, _ = AIEvaluation.objects.update_or_create(
            user_answer=answer,
            defaults={"transcription": text, "grammar_score": 4, "estimated_level": "B2"}
        )
        answer.grading_status = GradingStatusChoices.COMPLETE
        answer.save()
        return eval_obj