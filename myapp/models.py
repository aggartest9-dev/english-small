# myapp/models.py

from django.db import models, transaction
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    MaxLengthValidator,
)
from django.db.models import Q, F


# =====================================================
# BASE MODEL
# =====================================================

class GradingStatusChoices(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    PENDING = "pending", "Grading..."
    COMPLETE = "complete", "Complete"
    FAILED = "failed", "Failed"


class BaseModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
    )

    class Meta:
        abstract = True


# =====================================================
# COURSE DAY
# =====================================================

class CourseDay(BaseModel):
    class LevelChoices(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    level = models.CharField(
        max_length=20,
        choices=LevelChoices.choices,
        db_index=True,
    )

    day = models.PositiveSmallIntegerField(
        db_index=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(365),
        ],
    )

    title = models.CharField(
        max_length=255,
        db_index=True,
    )

    description = models.TextField(blank=True)

    is_published = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["level", "day"]

        constraints = [
            models.UniqueConstraint(
                fields=["level", "day"],
                name="uq_course_day_level_day",
            ),
        ]

        indexes = [
            models.Index(
                fields=["level", "is_published", "day"],
                name="idx_day_level_pub_day",
            ),
        ]

    def __str__(self):
        return f"{self.get_level_display()} - Day {self.day}"


# =====================================================
# LEARNING OBJECTIVE
# =====================================================

class LearningObjective(BaseModel):
    day = models.ForeignKey(
        CourseDay,
        on_delete=models.CASCADE,
        related_name="objectives",
    )

    text = models.CharField(max_length=255)

    order = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["order"]

        constraints = [
            models.UniqueConstraint(
                fields=["day", "order"],
                name="uq_objective_day_order",
            ),
        ]

        indexes = [
            models.Index(
                fields=["day", "is_active", "order"],
                name="idx_objective_day_act",
            ),
        ]

    def __str__(self):
        return self.text


# =====================================================
# CONTENT BLOCK
# =====================================================

class ContentBlock(BaseModel):
    class TypeChoices(models.TextChoices):
        VIDEO_LESSON = "video_lesson", "Video Lesson"
        TEXT_LESSON = "text_lesson", "Text Lesson"
        IMAGE_LESSON = "image_lesson", "Image Lesson"
        INTERACTIVE_QUESTION = "interactive_question", "Interactive Question"
        SPEAKING_TASK = "speaking_task", "Speaking Task"
        VIDEO_TASK = "video_task", "Video Task"
        WRITING_TASK = "writing_task", "Writing Task"
        AI_MESSAGE = "ai_message", "AI Message"
        COMMITMENT_TASK = "commitment_task", "Commitment Task"

    class MediaChoices(models.TextChoices):
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        IMAGE = "image", "Image"
        PDF = "pdf", "PDF"
        TEXT = "text", "TEXT"

    day = models.ForeignKey(
        CourseDay,
        on_delete=models.CASCADE,
        related_name="blocks",
    )

    depends_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unlocks",
    )

    section = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    order = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    block_type = models.CharField(
        max_length=40,
        choices=TypeChoices.choices,
        db_index=True,
    )
    media_type = models.CharField(
        max_length=20,
        choices=MediaChoices.choices,
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    text_content = models.TextField(blank=True,null=True)

    file_url = models.URLField(null=True, blank=True)
    subtitle_url = models.URLField(blank=True, null=True)
    thumbnail_url = models.URLField(blank=True, null=True)

    file_upload = models.FileField(upload_to="content_files/", null=True, blank=True)

    preAudio = models.URLField(null= True, blank = True)
    postAudio = models.URLField(null= True, blank = True)

    estimated_seconds = models.PositiveIntegerField(
        null=True,
        blank = True,
        validators=[MinValueValidator(1)],
    )

    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    unlock_after_completion = models.BooleanField(default=False)

    class Meta:
        ordering = ["section", "order"]

        constraints = [
            models.UniqueConstraint(
                fields=["day", "section", "order"],
                name="uq_block_day_section_order",
            ),
        ]

        indexes = [
            models.Index(
                fields=["day", "section", "order"],
                name="idx_block_position",
            ),
            models.Index(
                fields=["day", "is_active"],
                name="idx_block_day_active",
            ),
        ]

    def clean(self):
        if self.depends_on:
            if self.depends_on_id == self.id:
                raise ValidationError(
                    {"depends_on": "Block cannot depend on itself."}
                )

            if self.depends_on.day_id != self.day_id:
                raise ValidationError(
                    {"depends_on": "Dependency must belong to same day."}
                )
            
        if self.media_type == self.MediaChoices.TEXT:
            #self.file_url = None
            if not self.text_content:
                raise ValidationError({
                    "text_content": "Required when media type is TEXT."
            })

        else:
            if not self.file_url:
                raise ValidationError({
                    "file_url": "Required for non-text media types."
            })

    @property
    def final_file_url(self):
        """
        Logic to return the available file source.
        Prioritizes the local upload if both exist.
        """
        if self.file_upload:
            return self.file_upload.url
        return self.file_url

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.day} | S{self.section}-{self.order} | {self.title} | {self.media_type} | {self.final_file_url}"


# =====================================================
# QUESTION
# =====================================================

class Question(BaseModel):
    class FormatChoices(models.TextChoices):
        MCQ = "mcq", "Multiple Choice"
        SHORT = "short", "Short Answer"
        LONG = "long", "Long Answer"
        FILL_BLANK = "fill_blank", "Fill in Blank"
        SPEAKING = "speaking_prompt", "Speaking Prompt"
        VIDEO = "video_prompt", "Video Prompt"

    class ResponseChoices(models.TextChoices):
        OPTION = "option", "Select Option"
        TEXT = "text", "Text Response"
        AUDIO = "audio", "Audio Response"
        VIDEO = "video", "Video Response"
        MIXED = "mixed", "Mixed Response"

    class DifficultyChoices(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    block = models.ForeignKey(
        ContentBlock,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    format_type = models.CharField(
        max_length=30,
        choices=FormatChoices.choices,
        default=FormatChoices.MCQ,
    )

    response_type = models.CharField(
        max_length=20,
        choices=ResponseChoices.choices,
        default=ResponseChoices.OPTION,
    )

    difficulty = models.CharField(
        max_length=20,
        choices=DifficultyChoices.choices,
        default=DifficultyChoices.EASY,
    )

    text = models.TextField()

    preAudio = models.URLField(blank=True, null=True)
    postAudio = models.URLField(blank=True, null=True)

    timestamp_start = models.DecimalField(max_digits=8, decimal_places=2,blank=True, null=True)
    timestamp_end = models.DecimalField(max_digits=8, decimal_places=2,blank=True, null=True)

    auto_pause = models.BooleanField(default=True)
    resume_after_submit = models.BooleanField(default=True)

    marks = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    order = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ["timestamp_start", "order"]

        constraints = [
            models.UniqueConstraint(
            fields=["block", "timestamp_start"],
            condition=Q(timestamp_start__isnull=False),
            name="uq_question_block_ts"
                ),

            models.CheckConstraint(
                condition=(
                    Q(timestamp_start__isnull=True)
                    | Q(timestamp_end__isnull=True)
                    | Q(timestamp_end__gte=F("timestamp_start"))
                ),
                name="chk_question_valid_time",
            ),
        ]

        indexes = [
            models.Index(
                fields=["block", "timestamp_start", "order"],
                name="idx_question_time_order",
            ),
            models.Index(
                fields=["block", "is_active"],
                name="idx_question_block_active",
            ),
        ]

    def __str__(self):
        return self.text[:70]


# =====================================================
# OPTION
# =====================================================

class Option(BaseModel):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
    )

    text = models.CharField(max_length=255)

    is_correct = models.BooleanField(default=False)

    order = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        ordering = ["order"]

        constraints = [
            models.UniqueConstraint(
                fields=["question", "order"],
                name="uq_option_question_order",
            ),
        ]

        indexes = [
            models.Index(
                fields=["question", "order"],
                name="idx_option_question",
            ),
        ]

    def __str__(self):
        return self.text


# =====================================================
# USER ANSWER
# =====================================================

class UserAnswer(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="user_answers",
    )

    attempt_no = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    latest = models.BooleanField(
        default=True,
        db_index=True,
    )

    selected_option = models.ForeignKey(
        Option,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    text_answer = models.TextField(
        blank=True,
        validators=[MaxLengthValidator(5000)],
    )

    audio_file = models.FileField(
        upload_to="answers/audio/",
        blank=True,
        null=True,
    )

    video_file = models.FileField(
        upload_to="answers/video/",
        blank=True,
        null=True,
    )

    is_correct = models.BooleanField(
        default=False,
        db_index=True,
    )
    ai_feedback = models.JSONField(null=True, blank=True)
    grading_status = models.CharField(
        max_length=20,
        choices=GradingStatusChoices.choices,
        default=GradingStatusChoices.NOT_STARTED
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "question", "attempt_no"],
                name="uq_answer_attempt",
            ),
            models.UniqueConstraint(
                fields=["user", "question"],
                condition=Q(latest=True),
                name="uq_answer_latest",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "question"],
                name="idx_answer_user_q",
            ),
            models.Index(
                fields=["user", "question", "latest"],
                name="idx_answer_latest",
            ),
        ]

    def clean(self):
        if (
            self.selected_option
            and self.selected_option.question_id != self.question_id
        ):
            raise ValidationError(
                {"selected_option": "Option does not belong to question."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def create_attempt(cls, **kwargs):
        """
        Safe helper for concurrent answer submissions.
        """
        user = kwargs["user"]
        question = kwargs["question"]

        with transaction.atomic():
            cls.objects.select_for_update().filter(
                user=user,
                question=question,
            )

            last = cls.objects.filter(
                user=user,
                question=question,
            ).order_by("-attempt_no").first()

            next_attempt = 1 if not last else last.attempt_no + 1

            cls.objects.filter(
                user=user,
                question=question,
                latest=True,
            ).update(latest=False)

            kwargs["attempt_no"] = next_attempt
            kwargs["latest"] = True

            return cls.objects.create(**kwargs)

    def __str__(self):
        return f"{self.user} | Q{self.question_id} | Attempt {self.attempt_no}"

# =====================================================
# USER ANSWER Version
# =====================================================

class AnswerVersion(BaseModel):
    MAX_VERSIONS = 3  # ✅ enforce limit

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="answer_versions",
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answer_versions",
    )

    user_answer = models.ForeignKey(
        "UserAnswer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versions",
    )

    version_no = models.PositiveIntegerField()

    text_answer = models.TextField(blank=True)
    audio_file = models.FileField(upload_to="answers/audio/", null=True, blank=True)
    video_file = models.FileField(upload_to="answers/video/", null=True, blank=True)

    is_latest = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question", "version_no"],
                name="uq_version_user_question_version",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "question", "is_latest"],
                name="idx_version_latest_lookup",
            ),
        ]

    @classmethod
    def create_version(cls, **kwargs):
        user = kwargs["user"]
        question = kwargs["question"]

        with transaction.atomic():
            existing = (
                cls.objects
                .select_for_update()
                .filter(user=user, question=question)
                .order_by("-version_no")
            )

            # ❌ BLOCK after 3 attempts
            if existing.count() >= cls.MAX_VERSIONS:
                raise ValidationError("Maximum 3 attempts allowed.")

            latest = existing.first()
            next_version = 1 if not latest else latest.version_no + 1

            cls.objects.filter(
                user=user,
                question=question,
                is_latest=True
            ).update(is_latest=False)

            return cls.objects.create(
                version_no=next_version,
                is_latest=True,
                **kwargs
            )

# =====================================================
# USER PROGRESS
# =====================================================

class UserProgress(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="progress",
    )

    day = models.ForeignKey(
        CourseDay,
        on_delete=models.CASCADE,
        related_name="progress_entries",
    )

    is_started = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    progress_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-updated_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "day"],
                name="uq_progress_user_day",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "day"],
                name="idx_progress_user_day",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.day}"


# =====================================================
# USER COMMITMENT
# =====================================================

class UserCommitment(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="course_commitments",
    )

    day = models.ForeignKey(
        CourseDay,
        on_delete=models.CASCADE,
        related_name="user_commitments",
    )

    commitment_text = models.TextField(
        validators=[MaxLengthValidator(3000)],
    )

    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "day"],
                name="uq_commitment_user_day",
            ),
        ]

        indexes = [
            models.Index(
                fields=["user", "day"],
                name="idx_commitment_user_day",
            ),
        ]

    def __str__(self):
        return f"{self.user} - Day {self.day.day}"
    
class AIEvaluation(BaseModel):
    """
    Evaluates ALL versions of a submitted answer together.
    """

    user_answer = models.ForeignKey(
        UserAnswer,
        on_delete=models.CASCADE,
        related_name="evaluations",
    )

    versions = models.ManyToManyField(
        AnswerVersion,
        related_name="evaluations",
    )

    is_latest = models.BooleanField(default=True, db_index=True)

    # -------------------------
    # STATUS (async)
    # -------------------------
    class StatusChoices(models.TextChoices):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETE = "complete"
        FAILED = "failed"

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        db_index=True,
    )

    version_count = models.PositiveSmallIntegerField(default=1)

    # -------------------------
    # TRANSCRIPTS
    # -------------------------
    transcripts = models.JSONField(default=list)

    # -------------------------
    # SCORES
    # -------------------------
    grammar_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    vocabulary_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    clarity_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    coherence_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    fluency_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    relevance_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    # -------------------------
    # IMPROVEMENT
    # -------------------------
    improvement_score = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    improvement_summary = models.TextField(blank=True)

    version_comparison = models.JSONField(default=dict)

    # -------------------------
    # FEEDBACK
    # -------------------------
    errors = models.JSONField(default=list)
    strengths = models.JSONField(default=list)
    improvements = models.JSONField(default=list)

    estimated_level = models.CharField(max_length=20, blank=True)
    sentiment = models.CharField(max_length=50, blank=True)
    filler_words_count = models.IntegerField(default=0)

    # -------------------------
    # DEBUG
    # -------------------------
    raw_response = models.JSONField(null=True, blank=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_answer"],
                condition=Q(is_latest=True),
                name="uq_latest_eval_per_answer",
            )
        ]

        indexes = [
            models.Index(fields=["user_answer", "is_latest"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Eval {self.id} | Answer {self.user_answer_id} | {self.status}"