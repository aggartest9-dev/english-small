# myapp/admin.py

from django.contrib import admin
from django.db.models import Count, F
from django.utils.html import format_html

from .models import (
    CourseDay,
    LearningObjective,
    ContentBlock,
    Question,
    Option,
    UserAnswer,
    UserProgress,
    UserCommitment,
)


# =====================================================
# GLOBAL ADMIN BRANDING
# =====================================================

admin.site.site_header = "English Learning Platform Admin"
admin.site.site_title = "ELP Admin"
admin.site.index_title = "Enterprise Dashboard"


# =====================================================
# INLINES
# =====================================================

class LearningObjectiveInline(admin.TabularInline):
    model = LearningObjective
    extra = 1
    fields = (
        "order",
        "text",
        "is_active",
    )
    ordering = ("order",)


class OptionInline(admin.TabularInline):
    model = Option
    extra = 2
    fields = (
        "order",
        "text",
        "is_correct",
        "explanation",
    )
    ordering = ("order",)


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    fields = (
        ("order", "marks"),
        ("format_type", "response_type", "difficulty"),
        "text",
        ("prompt_audio", "prompt_video", "prompt_image"),
        ("timestamp_start", "timestamp_end"),
        ("auto_pause", "resume_after_submit"),
        ("is_required", "is_active"),
        "explanation",
        "preAudio",
        "postAudio",
      
    )
    ordering = (
        F("timestamp_start").asc(nulls_last=True),
        "order",
    )


class ContentBlockInline(admin.StackedInline):
    model = ContentBlock
    extra = 1
    fields = (
        ("section", "order"),
        "block_type",
        "title",
        "description",
        "text_content",
        "estimated_seconds",
        ("is_required", "is_active"),
        "unlock_after_completion",
        "depends_on",
        "preAudio",
        "postAudio",

    )
    ordering = ("section", "order")


# =====================================================
# COURSE DAY ADMIN
# =====================================================

@admin.register(CourseDay)
class CourseDayAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "level",
        "day",
        "is_published",
        "block_count",
        "created_at",
    )

    list_filter = (
        "level",
        "is_published",
    )

    search_fields = (
        "title",
        "description",
    )

    ordering = (
        "level",
        "day",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        LearningObjectiveInline,
        ContentBlockInline,
    ]

    list_per_page = 50

    actions = [
        "publish_days",
        "unpublish_days",
    ]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(total_blocks=Count("blocks"))
        )

    def block_count(self, obj):
        return obj.total_blocks

    block_count.short_description = "Blocks"
    block_count.admin_order_field = "total_blocks"

    def publish_days(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(
            request,
            f"{updated} course day(s) published."
        )

    def unpublish_days(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(
            request,
            f"{updated} course day(s) unpublished."
        )


# =====================================================
# CONTENT BLOCK ADMIN
# =====================================================

@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "day",
        "block_type",
        "section",
        "order",
        "estimated_seconds",
        "is_active",
        "question_count",
        "preAudio",
        "postAudio",
        "file_url",
        "file_upload",

        
        
    )

    list_filter = (
        "block_type",
        "is_active",
        "is_required",
        "day__level",
    )

    search_fields = (
        "title",
        "description",
        
    )

    autocomplete_fields = (
        "day",
        "depends_on",
    )

    ordering = (
        "day",
        "section",
        "order",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        QuestionInline,
    ]

    list_per_page = 50

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(total_questions=Count("questions"))
        )

    def question_count(self, obj):
        return obj.total_questions

    question_count.short_description = "Questions"


# =====================================================
# QUESTION ADMIN
# =====================================================

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "short_text",
        "block",
        "format_type",
        "response_type",
        "difficulty",
        "marks",
        "is_active",
        "option_count",
        "timestamp_start",
        "timestamp_end",
        "order",
        "preAudio",
        "postAudio",
    
    )

    list_filter = (
        "format_type",
        "response_type",
        "difficulty",
        "is_active",
        "is_required",
        "block__day__level",
    )

    search_fields = (
        "text",
        "explanation",
    )

    autocomplete_fields = ("block",)

    ordering = (
        "block",
        "timestamp_start",
        "order",
    )

    inlines = [OptionInline]

    list_per_page = 50

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(total_options=Count("options"))
        )

    def short_text(self, obj):
        return obj.text[:80]

    short_text.short_description = "Question"

    def option_count(self, obj):
        return obj.total_options

    option_count.short_description = "Options"


# =====================================================
# OPTION ADMIN
# =====================================================

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "text",
        "question",
        "is_correct",
        "order",
    )

    list_filter = (
        "is_correct",
    )

    search_fields = (
        "text",
    )

    autocomplete_fields = ("question",)

    ordering = (
        "question",
        "order",
    )


# =====================================================
# USER ANSWER ADMIN
# =====================================================

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "question_short",
        "attempt_no",
        "latest_badge",
        "is_correct",
        "created_at",
    )

    list_filter = (
        "is_correct",
        "latest",
        "question__response_type",
    )

    search_fields = (
        "user__username",
        "user__email",
        "question__text",
        "text_answer",
    )

    autocomplete_fields = (
        "user",
        "question",
        "selected_option",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    list_per_page = 50

    def question_short(self, obj):
        return obj.question.text[:70]

    question_short.short_description = "Question"

    def latest_badge(self, obj):
        if obj.latest:
            return format_html(
                '<span style="color:green;font-weight:bold;">YES</span>'
            )
        return format_html(
            '<span style="color:#999;">NO</span>'
        )

    latest_badge.short_description = "Latest"


# =====================================================
# USER PROGRESS ADMIN
# =====================================================

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "day",
        "is_started",
        "is_completed",
        "score",
        "progress_percent",
        "completed_at",
    )

    list_filter = (
        "is_started",
        "is_completed",
        "day__level",
    )

    search_fields = (
        "user__username",
        "user__email",
        "day__title",
    )

    autocomplete_fields = (
        "user",
        "day",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "completed_at",
    )

    ordering = ("-updated_at",)

    list_per_page = 50


# =====================================================
# USER COMMITMENT ADMIN
# =====================================================

@admin.register(UserCommitment)
class UserCommitmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "day",
        "short_commitment",
        "is_completed",
        "created_at",
    )

    list_filter = (
        "is_completed",
        "day__level",
    )

    search_fields = (
        "user__username",
        "user__email",
        "commitment_text",
    )

    autocomplete_fields = (
        "user",
        "day",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    list_per_page = 50

    def short_commitment(self, obj):
        return obj.commitment_text[:90]

    short_commitment.short_description = "Commitment"