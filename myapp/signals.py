# myapp/signals.py

from django.db import transaction
from django.db.models.signals import (
    post_save,
    post_delete,
    pre_save,
)
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    UserAnswer,
    UserProgress,
    UserCommitment,
    Question,
    ContentBlock,
    CourseDay,
)
from .services import ProgressService


# =====================================================
# USER ANSWER SIGNALS
# =====================================================

@receiver(pre_save, sender=UserAnswer)
def user_answer_pre_save(sender, instance, **kwargs):
    """
    Safety guard:
    If latest=True then all other attempts become latest=False.
    DB unique constraint also protects this.
    """
    if not instance.latest:
        return

    if not instance.user_id or not instance.question_id:
        return

    def cleanup_latest():
        (
            UserAnswer.objects
            .filter(
                user_id=instance.user_id,
                question_id=instance.question_id,
                latest=True,
            )
            .exclude(pk=instance.pk)
            .update(latest=False)
        )

    transaction.on_commit(cleanup_latest)


@receiver(post_save, sender=UserAnswer)
def user_answer_post_save(sender, instance, created, **kwargs):
    """
    Refresh progress whenever answer changes.
    """
    if not instance.user_id or not instance.question_id:
        return

    def refresh():
        ProgressService.refresh_day_progress(
            user=instance.user,
            day=instance.question.block.day,
        )

    transaction.on_commit(refresh)


@receiver(post_delete, sender=UserAnswer)
def user_answer_post_delete(sender, instance, **kwargs):
    """
    Recalculate after deletion.
    Also restore latest=True to newest remaining attempt.
    """
    if not instance.user_id or not instance.question_id:
        return

    def refresh():
        latest_remaining = (
            UserAnswer.objects
            .filter(
                user_id=instance.user_id,
                question_id=instance.question_id,
            )
            .order_by("-attempt_no", "-created_at")
            .first()
        )

        if latest_remaining:
            (
                UserAnswer.objects
                .filter(pk=latest_remaining.pk)
                .update(latest=True)
            )

        ProgressService.refresh_day_progress(
            user=instance.user,
            day=instance.question.block.day,
        )

    transaction.on_commit(refresh)


# =====================================================
# USER PROGRESS SIGNALS
# =====================================================

@receiver(pre_save, sender=UserProgress)
def user_progress_pre_save(sender, instance, **kwargs):
    """
    Auto-manage completed_at.
    """
    if instance.is_completed:
        if not instance.completed_at:
            instance.completed_at = timezone.now()
    else:
        instance.completed_at = None


# =====================================================
# USER COMMITMENT SIGNALS
# =====================================================

@receiver(pre_save, sender=UserCommitment)
def user_commitment_pre_save(sender, instance, **kwargs):
    """
    Clean text before save.
    """
    if instance.commitment_text:
        instance.commitment_text = instance.commitment_text.strip()


@receiver(post_save, sender=UserCommitment)
def user_commitment_post_save(sender, instance, created, **kwargs):
    """
    Reserved for:
    notifications / streaks / analytics / reminders
    """
    pass


# =====================================================
# CONTENT CHANGE SIGNALS
# =====================================================

@receiver(post_save, sender=Question)
def question_post_save(sender, instance, created, **kwargs):
    """
    If marks / required / active changes,
    progress may need recalculation for users.
    Hook reserved for async task queue.
    """
    pass


@receiver(post_delete, sender=Question)
def question_post_delete(sender, instance, **kwargs):
    """
    Reserved for future async recalculation.
    """
    pass


@receiver(post_save, sender=ContentBlock)
def content_block_post_save(sender, instance, created, **kwargs):
    """
    Reserved for:
    cache invalidation
    publish sync
    analytics rebuild
    """
    pass


@receiver(post_delete, sender=ContentBlock)
def content_block_post_delete(sender, instance, **kwargs):
    """
    Reserved for cache invalidation.
    """
    pass


@receiver(post_save, sender=CourseDay)
def course_day_post_save(sender, instance, created, **kwargs):
    """
    Reserved for cache warmup / sitemap / feed rebuild.
    """
    pass


# =====================================================
# ENTERPRISE NOTE
# =====================================================
# Ensure apps.py imports signals:
#
# class MyappConfig(AppConfig):
#     default_auto_field = "django.db.models.BigAutoField"
#     name = "myapp"
#
#     def ready(self):
#         import myapp.signals
#