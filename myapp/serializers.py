# myapp/serializers.py

from django.db import transaction
from django.db.models import Max
from rest_framework import serializers
from .utils import convert_link
from .services import AIEvaluation

from myapp.tasks.evaluation import evaluate_answer_task

from .models import (
    CourseDay,
    LearningObjective,
    ContentBlock,
    Question,
    Option,
    UserAnswer,
    UserProgress,
    UserCommitment,
    AIEvaluation,
    AnswerVersion,
)

# =====================================================
# CONSTANTS
# =====================================================

MAX_AUDIO_MB = 25
MAX_VIDEO_MB = 150
MAX_TEXT_ANSWER_LENGTH = 5000


# =====================================================
# HELPERS
# =====================================================

def validate_uploaded_file_size(file_obj, max_mb):
    if file_obj and file_obj.size > max_mb * 1024 * 1024:
        raise serializers.ValidationError(
            f"File size must be <= {max_mb} MB."
        )


def clean_text(value):
    if value is None:
        return ""
    return value.strip()



class AIEvaluationSerializer(serializers.ModelSerializer):
    summary_message = serializers.SerializerMethodField()

    class Meta:
        model = AIEvaluation
        fields = [
            "status",

            "version_count",
            "transcripts",

            "grammar_score",
            "vocabulary_score",
            "clarity_score",
            "coherence_score",
            "fluency_score",
            "confidence_score",
            "relevance_score",

            "improvement_score",
            "improvement_summary",
            "version_comparison",

            "sentiment",
            "estimated_level",
            "filler_words_count",

            "errors",
            "strengths",
            "improvements",

            "summary_message",
        ]

    def get_summary_message(self, obj):
        if obj.status != "complete":
            return "Evaluation in progress..."

        if obj.confidence_score and obj.confidence_score < 3:
            return "Good effort — try speaking more confidently."

        if obj.improvement_score > 1:
            return "Nice improvement between attempts!"

        return "Solid response. Keep practicing."




# =====================================================
# LEARNING OBJECTIVES
# =====================================================

class LearningObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningObjective
        fields = (
            "id",
            "text",
            "order",
        )



# =====================================================
# OPTION (PUBLIC)
# explanation hidden for learners
# =====================================================

class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = (
            "id",
            "text",
            "order",
        )


# =====================================================
# OPTION (ADMIN / INTERNAL)
# =====================================================

class OptionAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = (
            "id",
            "text",
            "order",
            "is_correct",
            "explanation",
        )


# =====================================================
# QUESTION
# =====================================================

class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(
        many=True,
        read_only=True
    )
    processed_pre_url = serializers.SerializerMethodField()
    processed_post_url = serializers.SerializerMethodField()
    

    format_label = serializers.CharField(
        source="get_format_type_display",
        read_only=True
    )

    response_label = serializers.CharField(
        source="get_response_type_display",
        read_only=True
    )

    difficulty_label = serializers.CharField(
        source="get_difficulty_display",
        read_only=True
    )

    class Meta:
        model = Question
        fields = (
            "id",

            "format_type",
            "format_label",

            "response_type",
            "response_label",

            "difficulty",
            "difficulty_label",

            "text",

            "timestamp_start",
            "timestamp_end",

            "auto_pause",
            "resume_after_submit",

            "marks",
            "order",

            "is_required",

            

            "preAudio",
            "postAudio",
            "processed_pre_url",
            "processed_post_url",
            "explanation",
            "options",
        )
    def get_processed_pre_url(self, obj):
        return convert_link(obj.preAudio)
    def get_processed_post_url(self, obj):
        return convert_link(obj.postAudio)


# =====================================================
# CONTENT BLOCK
# =====================================================

class ContentBlockSerializer(serializers.ModelSerializer):

    processed_pre_url = serializers.SerializerMethodField()
    processed_post_url = serializers.SerializerMethodField()

    questions = QuestionSerializer(
        many=True,
        read_only=True
    )

    block_type_label = serializers.CharField(
        source="get_block_type_display",
        read_only=True
    )

    class Meta:
        model = ContentBlock
        fields = (
            "id",

            "section",
            "order",

            "block_type",
            "block_type_label",
            "media_type",

            "title",
            "description",
            "text_content",

            "estimated_seconds",

            "is_required",
            "unlock_after_completion",

            "questions",
            "preAudio",
            "postAudio",
            "processed_pre_url",
            "processed_post_url",

            "final_file_url",
        )
    def get_processed_pre_url(self, obj):
        return convert_link(obj.preAudio)
    
    def get_processed_post_url(self, obj):
        return convert_link(obj.postAudio)


# =====================================================
# COURSE DAY DETAIL
# =====================================================

class CourseDaySerializer(serializers.ModelSerializer):
    objectives = LearningObjectiveSerializer(
        many=True,
        read_only=True
    )

    blocks = ContentBlockSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = CourseDay
        fields = (
            "id",
            "level",
            "day",
            "title",
            "description",
            "objectives",
            "blocks",
        )


# =====================================================
# COURSE DAY LIST
# =====================================================

class CourseDayListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseDay
        fields = (
            "id",
            "level",
            "day",
            "title",
        )


# =====================================================
# USER ANSWER HISTORY
# =====================================================

class UserAnswerHistorySerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(
        source="question.text",
        read_only=True
    )

    selected_option_text = serializers.CharField(
        source="selected_option.text",
        read_only=True
    )

    class Meta:
        model = UserAnswer
        fields = (
            "id",
            "question",
            "question_text",
            "selected_option",
            "selected_option_text",
            "text_answer",
            "attempt_no",
            "latest",
            "is_correct",
            "created_at",
        )


# =====================================================
# USER ANSWER SUBMIT
# =====================================================

class UserAnswerSerializer(serializers.ModelSerializer):

    ai_feedback = serializers.SerializerMethodField()
    status_label = serializers.CharField(
        source='get_grading_status_display',
        read_only=True
    )

    class Meta:
        model = UserAnswer
        fields = (
            "id",
            "question",
            "selected_option",

            "attempt_no",
            "latest",

            "is_correct",
            "grading_status",
            "status_label",

            "created_at",

            "ai_feedback",
        )

        read_only_fields = fields

    def get_ai_feedback(self, obj):
        latest_eval = obj.evaluations.filter(is_latest=True).first()
        if latest_eval:
            return AIEvaluationSerializer(latest_eval).data
        return None



class UserAnswerSubmitSerializer(serializers.Serializer):

    question = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.filter(is_active=True)
    )
    
    selected_option = serializers.PrimaryKeyRelatedField(
        queryset=Option.objects.all(),
        required=False,
        allow_null=True
    )

    def validate(self, attrs):
        user = self.context["request"].user
        question = attrs["question"]

        versions = AnswerVersion.objects.filter(
            user=user,
            question=question
        ).order_by("-created_at")[:3]

        if not versions:
            raise serializers.ValidationError(
                "At least one answer version required."
            )

        attrs["versions"] = list(versions)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        question = validated_data["question"]
        selected_option = validated_data.get("selected_option")
        versions = validated_data["versions"]

        # create UserAnswer
        user_answer = UserAnswer.create_attempt(
            user=user,
            question=question,
            selected_option=selected_option,
        )

        # create evaluation
        evaluation = AIEvaluation.objects.create(
            user_answer=user_answer,
            version_count=len(versions),
            status="pending",
        )

        evaluation.versions.set(versions)

        evaluate_answer_task.delay(evaluation.id)

        # attach versions
        AnswerVersion.objects.filter(
            id__in=[v.id for v in versions]
        ).update(user_answer=user_answer)

        # trigger async (later)
        # evaluate_answer.delay(evaluation.id)

        return user_answer

# =====================================================
# USER PROGRESS
# =====================================================

class UserProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProgress
        fields = (
            "id",
            "day",

            "is_started",
            "is_completed",

            "score",
            "progress_percent",

            "completed_at",
        )

        read_only_fields = (
            "id",
            "score",
            "progress_percent",
            "completed_at",
        )


# =====================================================
# USER COMMITMENT
# =====================================================

class UserCommitmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCommitment
        fields = (
            "id",
            "day",
            "commitment_text",
            "is_completed",
        )

        read_only_fields = (
            "id",
        )

    def validate_commitment_text(self, value):
        value = clean_text(value)

        if not value:
            raise serializers.ValidationError(
                "Commitment text cannot be empty."
            )

        return value
    

class AnswerVersionSerializer(serializers.ModelSerializer):

    class Meta:
        model = AnswerVersion
        fields = (
            "id",
            "question",
            "version_no",
            "text_answer",
            "audio_file",
            "video_file",
            "created_at",
        )
        read_only_fields = ("id", "version_no", "created_at")

    def validate_audio_file(self, value):
        validate_uploaded_file_size(value, MAX_AUDIO_MB)
        return value

    def validate_video_file(self, value):
        validate_uploaded_file_size(value, MAX_VIDEO_MB)
        return value

    def validate_text_answer(self, value):
        return clean_text(value)

    def create(self, validated_data):
        request = self.context["request"]

        return AnswerVersion.create_version(
            user=request.user,
            **validated_data
        )