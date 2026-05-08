# myapp/views.py

from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Prefetch

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)

from rest_framework.exceptions import (
    ValidationError,
    NotFound,
)

from rest_framework.parsers import (
    MultiPartParser,
    FormParser,
    JSONParser,
)

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import (
    CourseDay,
    ContentBlock,
    Question,
    UserAnswer,
    UserProgress,
    UserCommitment,
    AIEvaluation,
)

from .serializers import (
    CourseDaySerializer,
    CourseDayListSerializer,
    UserAnswerSerializer,
    UserAnswerHistorySerializer,
    UserProgressSerializer,
    UserCommitmentSerializer,
    AIEvaluationSerializer,
)

from .services import AIService, ProgressService


# =====================================================
# HEALTH CHECK
# =====================================================

def home(request):
    return JsonResponse({"status": "ok"})


# =====================================================
# SESSION LIST
# GET /api/sessions/?level=beginner
# =====================================================

class SessionListView(generics.ListAPIView):
    serializer_class = CourseDayListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = CourseDay.objects.filter(
            is_published=True
        )

        level = self.request.query_params.get("level")

        if level:
            queryset = queryset.filter(level=level)

        return queryset.order_by("level", "day")


# =====================================================
# SESSION DETAIL
# GET /api/sessions/detail/?level=beginner&day=1
# =====================================================

class SessionView(generics.RetrieveAPIView):
    serializer_class = CourseDaySerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "level",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                "day",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True
            ),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        level = self.request.query_params.get("level")
        day = self.request.query_params.get("day")

        if not level:
            raise ValidationError({"level": "Required."})

        try:
            day = int(day)
        except (TypeError, ValueError):
            raise ValidationError({"day": "Valid integer required."})

        try:
            return CourseDay.objects.prefetch_related(
                Prefetch(
                    "objectives",
                ),
                Prefetch(
                    "blocks",
                    queryset=ContentBlock.objects.filter(
                        is_active=True
                    ).prefetch_related(
                        "final_file_url",
                        Prefetch(
                            "questions",
                            queryset=Question.objects.filter(
                                is_active=True
                            ).prefetch_related(
                                "options"
                            )
                        )
                    )
                )
            ).get(
                level=level,
                day=day,
                is_published=True
            )

        except CourseDay.DoesNotExist:
            raise NotFound("Session not found.")


# =====================================================
# SUBMIT ANSWER
# POST /api/answers/
# =====================================================

class SubmitAnswerView(generics.CreateAPIView):
    serializer_class = UserAnswerSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]

    @transaction.atomic
    def perform_create(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)

        return Response(
            {
                "success": True,
                "message": "Answer submitted.",
                "data": response.data
            },
            status=status.HTTP_201_CREATED
        )


# =====================================================
# ANSWER HISTORY
# GET /api/answers/history/?question=1
# =====================================================

class AnswerHistoryView(generics.ListAPIView):
    serializer_class = UserAnswerHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = UserAnswer.objects.filter(
            user=self.request.user
        ).select_related(
            "question"
        )

        question_id = self.request.query_params.get("question")

        if question_id:
            queryset = queryset.filter(question_id=question_id)

        return queryset.order_by("-created_at")


# =====================================================
# UPDATE PROGRESS
# POST /api/progress/
# =====================================================

class ProgressUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        progress_percent = request.data.get(
            "progress_percent",
            0
        )

        is_completed = serializer.validated_data.get(
            "is_completed",
            False
        )

        defaults = {
            "is_started": serializer.validated_data.get(
                "is_started",
                True
            ),
            "is_completed": is_completed,
            "progress_percent": progress_percent,
        }

        if is_completed:
            defaults["completed_at"] = timezone.now()

        obj, created = UserProgress.objects.update_or_create(
            user=request.user,
            day=serializer.validated_data["day"],
            defaults=defaults
        )

        return Response({
            "success": True,
            "message": "Progress saved."
        })


# =====================================================
# MY PROGRESS LIST
# GET /api/progress/
# =====================================================

class ProgressListView(generics.ListAPIView):
    serializer_class = UserProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserProgress.objects.filter(
            user=self.request.user
        ).select_related(
            "day"
        ).order_by("-updated_at")


# =====================================================
# PROGRESS DETAIL
# GET /api/progress/day/1/
# =====================================================

class ProgressDetailView(generics.RetrieveAPIView):
    serializer_class = UserProgressSerializer
    permission_classes = [IsAuthenticated]

    lookup_url_kwarg = "day_id"

    def get_object(self):
        day_id = self.kwargs.get("day_id")

        try:
            return UserProgress.objects.get(
                user=self.request.user,
                day_id=day_id
            )
        except UserProgress.DoesNotExist:
            raise NotFound("Progress not found.")


# =====================================================
# SAVE COMMITMENT
# POST /api/commitments/
# =====================================================

class CommitmentCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserCommitmentSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        obj, created = UserCommitment.objects.update_or_create(
            user=request.user,
            day=serializer.validated_data["day"],
            defaults={
                "commitment_text":
                    serializer.validated_data[
                        "commitment_text"
                    ],
                "is_completed":
                    serializer.validated_data.get(
                        "is_completed",
                        False
                    )
            }
        )

        return Response({
            "success": True,
            "message": "Commitment saved."
        })


# =====================================================
# LAST COMMITMENT
# GET /api/commitments/last/
# =====================================================

class CommitmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        obj = UserCommitment.objects.filter(
            user=request.user
        ).select_related(
            "day"
        ).order_by("-updated_at").first()

        if not obj:
            return Response({
                "success": True,
                "data": None
            })

        serializer = UserCommitmentSerializer(obj)

        return Response({
            "success": True,
            "data": serializer.data
        })


# =====================================================
# ALL MY COMMITMENTS
# GET /api/commitments/
# =====================================================

class CommitmentListView(generics.ListAPIView):
    serializer_class = UserCommitmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserCommitment.objects.filter(
            user=self.request.user
        ).select_related(
            "day"
        ).order_by("-updated_at")



class NextSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Find the last completed day
        last_progress = UserProgress.objects.filter(
            user=request.user, 
            is_completed=True
        ).order_by('-day__day').first()
        
        next_day_num = (last_progress.day.day + 1) if last_progress else 1
        
        # Logic to return the next CourseDay...
        return Response({"next_day": next_day_num})
    

class FinalizeSessionView(APIView):
    """
    Called when the user finishes the day. 
    Triggers AI for all answers from that day.
    """
    def post(self, request):
        user = request.user
        day_id = request.data.get("day_id")
        use_mock = request.data.get("use_mock", False) # For your testing

        answers = UserAnswer.objects.filter(
            user=user, 
            question__block__day_id=day_id, 
            latest=True
        )

        for ans in answers:
            # In real production, this should be a Celery task!
            # For now, we run it sync so you can see the result.
            AIService.evaluate_answer(ans.id, use_mock=use_mock)

        return Response({"status": "Grading complete", "count": answers.count()})

class ManualCheckView(APIView):
    """For testing: Grade a single specific answer."""
    def post(self, request):
        # 1. Safely extract data from the request
        ans_id = request.data.get("answer_id")
        # Default to True so you don't accidentally spend OpenAI credits
        use_mock = request.data.get("use_mock", True) 

        # 2. Check if the ID was even provided
        if not ans_id:
            return Response(
                {"error": "Please provide an 'answer_id' in the JSON body."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 3. Try to run the evaluation
            eval_obj = AIService.evaluate_answer(ans_id, use_mock=use_mock)
            return Response({
                "message": "Grading successful", 
                "estimated_level": eval_obj.estimated_level,
                "confidence": eval_obj.confidence_score
            })
            
        except UserAnswer.DoesNotExist:
            # 4. Handle the case where the ID is simply not in the DB
            return Response(
                {"error": f"No UserAnswer found with ID {ans_id}."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # 5. Catch other errors (like OpenAI API issues)
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )