# myapp/urls.py

from django.urls import path

from .views import (
    home,
    SessionView,
    SubmitAnswerView,
    ProgressUpdateView,
    CommitmentCreateView,
    CommitmentDetailView,
    FinalizeSessionView,
    ManualCheckView,
)

app_name = "myapp"

urlpatterns = [

    # ==================================================
    # SYSTEM / HEALTH CHECK
    # ==================================================
    path(
        "",
        home,
        name="home",
    ),

    # ==================================================
    # COURSE SESSION CONTENT
    # GET /api/sessions/?level=beginner&day=1
    # ==================================================
    path(
        "sessions/",
        SessionView.as_view(),
        name="session-detail",
    ),

    # ==================================================
    # ANSWERS
    # POST /api/answers/
    # ==================================================
    path(
        "answers/",
        SubmitAnswerView.as_view(),
        name="submit-answer",
    ),

    # Trigger AI grading for the whole day at once
    path("sessions/finalize/", FinalizeSessionView.as_view(), name="session-finalize"),
    
    # Endpoint for your manual testing/admin checks
    path("admin/manual-grade/", ManualCheckView.as_view(), name="manual-grade"),

    # ==================================================
    # USER PROGRESS
    # POST /api/progress/
    # ==================================================
    path(
        "progress/",
        ProgressUpdateView.as_view(),
        name="progress-update",
    ),

    # ==================================================
    # USER COMMITMENTS
    # POST /api/commitments/
    # ==================================================
    path(
        "commitments/",
        CommitmentCreateView.as_view(),
        name="commitment-save",
    ),

    # ==================================================
    # LATEST USER COMMITMENT
    # GET /api/commitments/latest/
    # ==================================================
    path(
        "commitments/latest/",
        CommitmentDetailView.as_view(),
        name="commitment-latest",
    ),
]