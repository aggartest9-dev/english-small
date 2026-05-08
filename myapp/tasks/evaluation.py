from celery import shared_task
from django.utils import timezone
from django.db import transaction
import time

from myapp.models import AIEvaluation, GradingStatusChoices


MAX_AI_RETRIES = 2


@shared_task(bind=True, max_retries=MAX_AI_RETRIES)
def evaluate_answer_task(self, evaluation_id):
    start_time = time.time()

    try:
        evaluation = (
            AIEvaluation.objects
            .select_related("user_answer", "user_answer__question")
            .prefetch_related("versions")
            .get(id=evaluation_id)
        )

        # prevent duplicate processing
        if evaluation.status in ["processing", "complete"]:
            return

        evaluation.status = "processing"
        evaluation.save(update_fields=["status"])

        versions = list(evaluation.versions.all().order_by("version_no"))

        # -------------------------
        # STEP 1: TRANSCRIPTION
        # -------------------------
        transcripts = []

        for v in versions:
            transcript = handle_transcription(v)
            transcripts.append({
                "version": v.version_no,
                "text": transcript
            })

        # -------------------------
        # STEP 2: LLM EVALUATION
        # -------------------------
        result = call_llm_evaluation(
            question=evaluation.user_answer.question.text,
            transcripts=transcripts
        )

        # -------------------------
        # STEP 3: SAVE RESULT
        # -------------------------
        with transaction.atomic():
            evaluation.transcripts = transcripts

            evaluation.grammar_score = result.get("grammar_score", 0)
            evaluation.vocabulary_score = result.get("vocabulary_score", 0)
            evaluation.clarity_score = result.get("clarity_score", 0)
            evaluation.coherence_score = result.get("coherence_score", 0)
            evaluation.fluency_score = result.get("fluency_score", 0)
            evaluation.confidence_score = result.get("confidence_score", 0)
            evaluation.relevance_score = result.get("relevance_score", 0)

            evaluation.improvement_score = result.get("improvement_score", 0)
            evaluation.improvement_summary = result.get("improvement_summary", "")
            evaluation.version_comparison = result.get("version_comparison", {})

            evaluation.errors = result.get("errors", [])
            evaluation.strengths = result.get("strengths", [])
            evaluation.improvements = result.get("improvements", [])

            evaluation.estimated_level = result.get("estimated_level", "")
            evaluation.sentiment = result.get("sentiment", "")
            evaluation.filler_words_count = result.get("filler_words_count", 0)

            evaluation.raw_response = result

            evaluation.status = "complete"

            evaluation.processing_time_ms = int((time.time() - start_time) * 1000)

            evaluation.save()

            # update UserAnswer
            ua = evaluation.user_answer
            ua.grading_status = GradingStatusChoices.COMPLETE
            ua.save(update_fields=["grading_status"])

    except Exception as exc:
        handle_failure(self, evaluation_id, exc)



def handle_failure(task, evaluation_id, exc):
    try:
        evaluation = AIEvaluation.objects.get(id=evaluation_id)
    except AIEvaluation.DoesNotExist:
        return

    if task.request.retries >= MAX_AI_RETRIES:
        evaluation.status = "failed"
        evaluation.save(update_fields=["status"])

        ua = evaluation.user_answer
        ua.grading_status = GradingStatusChoices.FAILED
        ua.save(update_fields=["grading_status"])
        return

    raise task.retry(exc=exc, countdown=30)

def handle_transcription(version):
    """
    Decide how to extract text from version
    """

    if version.text_answer:
        return version.text_answer

    if version.audio_file:
        return transcribe_audio(version.audio_file.path)

    if version.video_file:
        return transcribe_video(version.video_file.path)

    return ""


def transcribe_audio(file_path):
    # plug Whisper / Deepgram later
    return "transcribed audio text"


def transcribe_video(file_path):
    return "transcribed video text"


def call_llm_evaluation(question, transcripts):
    """
    Central place for LLM interaction
    """

    payload = {
        "question": question,
        "versions": transcripts
    }

    # 🔥 Replace with OpenAI / your provider
    return mock_llm(payload)



def mock_llm(payload):
    return {
        "grammar_score": 7.5,
        "vocabulary_score": 6.8,
        "clarity_score": 7.0,
        "coherence_score": 6.5,
        "fluency_score": 7.2,
        "confidence_score": 3.5,
        "relevance_score": 8.0,

        "improvement_score": 1.5,
        "improvement_summary": "User improved clarity in later attempts.",

        "version_comparison": {
            "v1_vs_v2": "better fluency",
            "v2_vs_v3": "minor grammar fixes"
        },

        "errors": [],
        "strengths": ["clear pronunciation"],
        "improvements": ["reduce filler words"],

        "estimated_level": "B1",
        "sentiment": "Positive",
        "filler_words_count": 3,
    }
