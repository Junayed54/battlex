# tournaments/views.py
import random
import pandas as pd
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from collections import defaultdict
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAdminUser # Or your custom permission
from django.db import transaction
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404 # Although serializer PrimaryKeyRelatedField handles this

from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.http import Http404
from users.middleware import CombinedJWTOrGuestAuthentication 
from .serializers import *
from .models import *
from quiz.models import Question, Option # Adjust import if quiz app is structured differently
from quiz.serializers import QuestionSerializer # Assuming you have a serializer for Question

# from rest_framework_simplejwt.tokens import AccessToken

# Helper function to process the excel file (re-used from previous example)
def process_excel_for_questions(file, tournament):
    """
    Reads an Excel file with columns: Question, Option1, Option2, Option3, Option4, Answer
    Creates/updates Questions and Options, and marks the correct option based on Answer.
    Answer can be:
      - Exact option text (case insensitive match)
      - Option letter 'a', 'b', 'c', 'd' (case insensitive)
      - Literal string 'option1', 'option2', 'option3', 'option4' (case insensitive)
      - Exact question text (means the question itself is the answer, treat as correct option if matches)
    """
    try:
        df = pd.read_excel(file)
    except Exception as e:
        raise ValueError(f"Could not read Excel file. Ensure it's a valid .xlsx format. Error: {e}")

    # Normalize column names for case-insensitive access
    df.columns = df.columns.str.strip().str.lower()

    # Rename columns if necessary for consistency
    df.rename(columns=lambda x: x.replace(' ', '').replace('_', ''), inplace=True)

    processed_questions = []
    added_question_ids_this_batch = set()

    # Map option letters to indices (0-based)
    option_letter_map = {'a': 0, 'b': 1, 'c': 2, 'd': 3}
    # Map literal option names to indices (0-based)
    option_name_map = {'option1': 0, 'option2': 1, 'option3': 2, 'option4': 3}

    with transaction.atomic():
        for index, row in df.iterrows():
            row_num = index + 2

            question_text = row.get('question') or row.get('questiontext')
            if not question_text or pd.isna(question_text):
                raise ValueError(f"Row {row_num}: 'Question' column is missing or empty.")

            question_text = str(question_text).strip()

            # Extract options in a list, ignoring missing options
            options = []
            for i in range(1, 5):  # For option1 to option4
                opt = row.get(f'option{i}')
                if pd.isna(opt):
                    options.append(None)
                else:
                    options.append(str(opt).strip())

            # Get the answer value
            answer_raw = row.get('answer')
            if answer_raw is None or pd.isna(answer_raw):
                raise ValueError(f"Row {row_num}: 'Answer' column is missing or empty.")

            answer_raw_str = str(answer_raw).strip().lower()

            # Create or get question
            question = Question.objects.create(
                question_text=question_text
            )

            created = True

            options_to_create = []
            correct_option_found = False

            for idx, opt_text in enumerate(options):
                if not opt_text:
                    continue

                is_correct = False

                # Check if answer matches option letter (a,b,c,d)
                if answer_raw_str in option_letter_map:
                    if option_letter_map[answer_raw_str] == idx:
                        is_correct = True
                        correct_option_found = True
                # Check if answer matches literal option name 'option1', 'option2', etc.
                elif answer_raw_str in option_name_map:
                    if option_name_map[answer_raw_str] == idx:
                        is_correct = True
                        correct_option_found = True
                # Check if answer matches option text exactly (case insensitive)
                elif opt_text.lower() == answer_raw_str:
                    is_correct = True
                    correct_option_found = True
                # Check if answer matches question text exactly (means whole question is answer)
                elif question_text.lower() == answer_raw_str:
                    # If answer matches question text, mark first option as correct (optional)
                    if idx == 0:
                        is_correct = True
                        correct_option_found = True

                options_to_create.append(
                    Option(
                        question=question,
                        option_text=opt_text,
                        is_correct=is_correct
                    )
                )

            if len(options_to_create) == 0:
                raise ValueError(f"Row {row_num}: No options found for question '{question_text}'.")

            if not correct_option_found:
                raise ValueError(f"Row {row_num}: No correct option matched for question '{question_text}' with answer '{answer_raw}'.")

            # Bulk create options
            Option.objects.bulk_create(options_to_create)

            if question.id not in added_question_ids_this_batch:
                tournament.questions.add(question)
                processed_questions.append(question)
                added_question_ids_this_batch.add(question.id)

    return processed_questions

class TournamentQuestionUploadAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    
    def post(self, request, *args, **kwargs):
            serializer = TournamentQuestionUploadSerializer(data=request.data)

            if serializer.is_valid():
                tournament = serializer.validated_data['tournament']
                excel_file = serializer.validated_data['excel_file']

                try:
                    processed_questions = process_excel_for_questions(excel_file, tournament)

                    return Response({
                        "type": "success",
                        "message": f"Successfully uploaded {len(processed_questions)} questions and added them to tournament '{tournament.title}'.",
                        "data": {}
                    }, status=200)  # Always 200

                except ValueError as e:
                    return Response({
                        "type": "error",
                        "message": str(e),
                        "data": {}
                    }, status=200)  # Always 200

                except IntegrityError as e:
                    return Response({
                        "type": "error",
                        "message": f"Database integrity error during upload: {e}. Check for duplicate data or constraints.",
                        "data": {}
                    }, status=200)  # Always 200

                except Exception as e:
                    return Response({
                        "type": "error",
                        "message": f"An unexpected error occurred during file processing: {e}",
                        "data": {}
                    }, status=200)  # Always 200

            else:
                return Response({
                    "type": "error",
                    "message": "Invalid input data.",
                    "data": serializer.errors
                }, status=200)  # Always 200
                
            
            
def success_response(message: str, data: dict = None, status_code=status.HTTP_200_OK):
    """
    Constructs a standardized success response.
    """
    if data is None:
        data = {}
    return Response({
        "type": "success",
        "message": message,
        "data": data
    }, status=status_code)

def error_response(message: str, data: dict = None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Constructs a standardized error response.
    Defaults to HTTP_400_BAD_REQUEST for errors, but can be overridden.
    """
    if data is None:
        data = {}
    return Response({
        "type": "error",
        "message": message,
        "data": data
    }, status=status_code)
            
class TournamentListView(generics.ListAPIView):
    queryset = Tournament.objects.filter(end_date__gte=timezone.now()).order_by('-start_date')
    serializer_class = TournamentSerializer
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response("Active tournaments fetched successfully.", serializer.data)
    
    
    

class TournamentDetailView(generics.RetrieveAPIView):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response("Tournament details fetched successfully.", serializer.data)

class TournamentPrizeListView(generics.ListAPIView):
    serializer_class = TournamentPrizeSerializer
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def get_queryset(self):
        tournament_id = self.kwargs.get('tournament_id')
        return TournamentPrize.objects.filter(tournament_id=tournament_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response("Tournament prizes fetched successfully.", serializer.data)

class TournamentWinnerListView(generics.ListAPIView):
    serializer_class = TournamentWinnerSerializer
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def get_queryset(self):
        tournament_id = self.kwargs.get('tournament_id')
        return TournamentWinner.objects.filter(tournament_id=tournament_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response("Tournament winners fetched successfully.", serializer.data)
    
    
    
class TournamentLeaderboardListView(generics.ListAPIView):
    serializer_class = TournamentLeaderboardSerializer
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def get_queryset(self):
        tournament_id = self.kwargs.get('tournament_id')
        return TournamentLeaderboard.objects.filter(tournament_id=tournament_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response("Leaderboard data fetched successfully.", serializer.data)
# User Views

class UserTournamentAttemptListView(generics.ListAPIView):
    serializer_class = TournamentAttemptSerializer
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def get_queryset(self):
        return TournamentAttempt.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response("Tournament attempts fetched successfully.", serializer.data)
# Admin Views

class AdminTournamentListCreateView(generics.ListCreateAPIView):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as e:
            return Response({
                "type": "error",
                "message": "Validation Error",
                "data": e.detail  # This contains {'field_name': ['error message']}
            }, status=status.HTTP_200_OK)

        self.perform_create(serializer)
        return Response({
            "type": "success",
            "message": "Tournament created successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "type": "success",
            "message": "Tournaments retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    

class AdminTournamentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response("Tournament details fetched successfully.", serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response("Tournament updated successfully.", serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return success_response("Tournament deleted successfully.", {})


class AdminTournamentPrizeListCreateView(generics.ListCreateAPIView):
    serializer_class = TournamentPrizeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tournament_id = self.kwargs.get('tournament_id')
        return TournamentPrize.objects.filter(tournament_id=tournament_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response("Tournament prize list fetched successfully.", serializer.data)

    def create(self, request, *args, **kwargs):
        tournament_id = self.kwargs.get('tournament_id')
        tournament = get_object_or_404(Tournament, pk=tournament_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(tournament=tournament)
        return success_response("Tournament prize created successfully.", serializer.data)

class AdminTournamentPrizeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TournamentPrize.objects.all()
    serializer_class = TournamentPrizeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'prize_id'

    def retrieve(self, request, *args, **kwargs):
        try:
            response = super().retrieve(request, *args, **kwargs)
            return success_response(
                "Tournament prize details fetched successfully.", 
                response.data, 
                status_code=status.HTTP_200_OK # Explicitly 200 OK
            )
        except Http404:
            return error_response(
                "Tournament prize not found.", 
                status_code=status.HTTP_200_OK # Explicitly 200 OK for not found
            )
        except Exception as e:
            print(f"Error retrieving tournament prize: {e}")
            return error_response(
                f"An unexpected error occurred: {str(e)}", 
                status_code=status.HTTP_200_OK # Explicitly 200 OK for errors
            )

    def update(self, request, *args, **kwargs):
        try:
            response = super().update(request, *args, **kwargs)
            return success_response(
                "Tournament prize updated successfully.", 
                response.data, 
                status_code=status.HTTP_200_OK # Explicitly 200 OK
            )
        except Http404:
            return error_response(
                "Tournament prize not found for update.", 
                status_code=status.HTTP_200_OK # Explicitly 200 OK for not found
            )
        except ValidationError as e:
            return error_response(
                "Validation failed.", 
                e.detail, 
                status_code=status.HTTP_200_OK # Explicitly 200 OK for validation errors
            )
        except Exception as e:
            print(f"Error updating tournament prize: {e}")
            return error_response(
                f"An unexpected error occurred: {str(e)}", 
                status_code=status.HTTP_200_OK # Explicitly 200 OK for errors
            )

    def destroy(self, request, *args, **kwargs):
        try:
            super().destroy(request, *args, **kwargs)
            return success_response(
                "Tournament prize deleted successfully.", 
                {}, 
                status_code=status.HTTP_200_OK # Explicitly 200 OK for successful deletion
            )
        except Http404:
            return error_response(
                "Tournament prize not found for deletion.", 
                status_code=status.HTTP_200_OK # Explicitly 200 OK for not found
            )
        except Exception as e:
            print(f"Error deleting tournament prize: {e}")
            return error_response(
                f"An unexpected error occurred: {str(e)}", 
                status_code=status.HTTP_200_OK # Explicitly 200 OK for errors
            )

class AdminTournamentWinnerListView(generics.ListAPIView):
    queryset = TournamentWinner.objects.all()
    serializer_class = TournamentWinnerSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filterset_fields = ['tournament', 'claim_status', 'prize__prize_type']
    search_fields = ['user__email', 'guest_user__id', 'tournament__title', 'prize__title']

    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs)
            data = response.data
            return success_response(
                "Tournament winners fetched successfully.", 
                data, 
                status_code=status.HTTP_200_OK # Explicitly 200 OK
            )
        except Exception as e:
            print(f"Error in AdminTournamentWinnerListView: {e}") 
            return error_response(
                f"An unexpected error occurred: {str(e)}", 
                status_code=status.HTTP_200_OK # Explicitly 200 OK for errors
            )



# Utility
def get_user_or_guest(request):
    # user = request.user if request.user.is_authenticated else None
    # guest_user = None

    if isinstance(request.user, User):
        user = request.user
        guest_user = None
    elif isinstance(request.user, UserOpenAccount):
        user = None
        guest_user = request.user
    # if not user:
    #     guest_user_id = request.headers.get('X-Guest-User-ID')
    #     if guest_user_id:
    #         try:
    #             guest_user = UserOpenAccount.objects.get(pk=guest_user_id)
    #         except UserOpenAccount.DoesNotExist:
    #             raise ValidationError("Invalid Guest User ID provided.")
    return user, guest_user

def get_unique_tournament_questions_for_user(tournament, user=None, guest_user=None):
    if not (user or guest_user):
        print(user, guest_user)
        raise ValueError("Either user or guest_user must be provided.")

    query_filter = Q(tournament=tournament, is_completed=True)
    if user:
        query_filter &= Q(user=user)
    elif guest_user:
        query_filter &= Q(guest_user=guest_user)

    previous_attempts = TournamentAttempt.objects.filter(query_filter)
    previously_attempted_ids = set()
    for attempt in previous_attempts:
        previously_attempted_ids.update(attempt.questions_attempted.values_list('id', flat=True))

    all_questions = list(tournament.questions.all())
    available_questions = [q for q in all_questions if q.id not in previously_attempted_ids]

    if len(available_questions) < tournament.max_questions_per_attempt:
        if not available_questions:
            raise ValidationError("You have attempted all unique questions.")
        selected_questions = available_questions
    else:
        selected_questions = random.sample(available_questions, tournament.max_questions_per_attempt)

    return selected_questions

# Class-based API View to start attempt
class StartTournamentAttemptView(APIView):
    
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = StartTournamentAttemptSerializer(data=request.data)
        if not serializer.is_valid():
            print(serializer.errors)
            return Response({
                "type": "error",
                "message": "Invalid data provided",
                "data": {
                    "errors": serializer.errors
                }
            }, status=status.HTTP_200_OK)

        
        tournament = serializer.validated_data['tournament']
        user, guest_user = get_user_or_guest(request)
        # print(user, guest)
        if not (user or guest_user):
            return Response({
                "type": "error",
                "message": "Authentication or Guest User ID is required.",
                "data": {}
            }, status=status.HTTP_200_OK)

        now = timezone.now()
        if not (tournament.start_date <= now <= tournament.end_date and tournament.status == 'active'):
            return Response({
                "type": "error",
                "message": "Tournament is not currently active.",
                "data": {}
            }, status=status.HTTP_200_OK)

        # Check total attempts
        base_filter = Q(tournament=tournament, is_completed=True)
        if user:
            base_filter &= Q(user=user)
        elif guest_user:
            base_filter &= Q(guest_user=guest_user)

        total_attempts = TournamentAttempt.objects.filter(base_filter).count()
        if tournament.max_total_attempts is not None and total_attempts >= tournament.max_total_attempts:
            return Response({
                "type": "error",
                "message": "Maximum total attempts reached.",
                "data": {}
            }, status=status.HTTP_200_OK)

        # Check daily attempts
        today_start = timezone.make_aware(timezone.datetime.combine(now.date(), timezone.datetime.min.time()))
        today_end = timezone.make_aware(timezone.datetime.combine(now.date(), timezone.datetime.max.time()))
        daily_attempts = TournamentAttempt.objects.filter(
            base_filter & Q(attempt_date__range=(today_start, today_end))
        ).count()
        if daily_attempts >= tournament.max_attempts_per_day:
            return Response({
                "type": "error",
                "message": "Maximum daily attempts reached.",
                "data": {}
            }, status=status.HTTP_200_OK)
        
        
        try:
            
            questions = get_unique_tournament_questions_for_user(tournament, user, guest_user)
            # print(questions)
        except ValidationError as e:
            # print("hello questions")
            return Response({
                "type": "error",
                "message": str(e),
                "data": {}
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({
                "type": "error",
                "message": str(e),
                "data": {}
            }, status=status.HTTP_200_OK)

        with transaction.atomic():
            attempt = TournamentAttempt.objects.create(
                user=user,
                guest_user=guest_user,
                tournament=tournament,
                attempt_date=now
            )
            attempt.questions_attempted.set(questions)

        return Response({
            "type": "success",
            "message": "Tournament attempt started successfully.",
            "data": {
                "attempt_id": attempt.id,
                "tournament_id": tournament.id,
                "duration_minutes": tournament.duration_minutes,
                "max_questions_per_attempt": tournament.max_questions_per_attempt,
                "questions": QuestionSerializer(questions, many=True).data
            }
        }, status=status.HTTP_200_OK)
        
class SubmitTournamentAttemptView(APIView):
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = SubmitTournamentAttemptSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "type": "error",
                "message": "Invalid data provided",
                "data": {
                    "errors": serializer.errors
                }
            }, status=status.HTTP_200_OK)

        attempt = serializer.validated_data['attempt_id']
        answers_data = serializer.validated_data['answers']
        user, guest_user = get_user_or_guest(request)

        # Ownership check
        if user and attempt.user != user:
            raise PermissionDenied("This attempt does not belong to the authenticated user.")
        elif guest_user and attempt.guest_user != guest_user:
            raise PermissionDenied("This attempt does not belong to the provided guest user.")
        elif not user and not guest_user:
            raise PermissionDenied("Authentication or Guest User ID is required.")

        if attempt.is_completed:
            return Response({
                "type": "error",
                "message": "This attempt has already been submitted.",
                "data": {}
            }, status=status.HTTP_200_OK)

        now = timezone.now()
        tournament = attempt.tournament

        # if tournament.duration_minutes > 0:
        #     allowed_end = attempt.attempt_date + timedelta(minutes=tournament.duration_minutes)
        #     if now > allowed_end:
        #         return Response({
        #             "type": "error",
        #             "message": "Time limit exceeded.",
        #             "data": {}
        #         }, status=status.HTTP_200_OK)

        if not (tournament.start_date <= now <= tournament.end_date and tournament.status == 'active'):
            return Response({
                "type": "error",
                "message": "Tournament is no longer active.",
                "data": {}
            }, status=status.HTTP_200_OK)

        correct = 0
        wrong = 0
        answered_ids = set()

        questions = Question.objects.filter(
            id__in=attempt.questions_attempted.values_list('id', flat=True)
        ).prefetch_related('options')
        question_map = {q.id: q for q in questions}

        for answer in answers_data:
            q_id = answer.get('question_id')
            opt_id = answer.get('selected_option_id')

            if not q_id or not opt_id:
                raise ValidationError("Each answer must include 'question_id' and 'selected_option_id'.")

            question = question_map.get(q_id)
            if not question:
                raise ValidationError(f"Question {q_id} not part of this attempt.")

            answered_ids.add(q_id)

            try:
                selected_option = question.options.get(id=opt_id)
            except Option.DoesNotExist:
                raise ValidationError(f"Option {opt_id} not valid for question {q_id}.")

            if selected_option.is_correct:
                correct += 1
            else:
                wrong += 1

        skipped = attempt.questions_attempted.count() - len(answered_ids)

        with transaction.atomic():
            attempt.correct_answers = correct
            attempt.wrong_answers = wrong
            attempt.skipped_questions = skipped
            attempt.end_time = now
            attempt.time_taken_seconds = int((now - attempt.attempt_date).total_seconds())
            attempt.is_completed = True
            attempt.calculate_score()

            leaderboard, created = TournamentLeaderboard.objects.get_or_create(
                user=user,
                guest_user=guest_user,
                tournament=tournament,
                defaults={
                    'total_score': attempt.score,
                    'last_daily_score': attempt.score,
                    'last_daily_update': now.date(),
                    'last_attempt_datetime': now
                }
            )

            if not created:
                if attempt.score > leaderboard.total_score:
                    leaderboard.total_score = attempt.score
                    leaderboard.last_attempt_datetime = now

                if leaderboard.last_daily_update == now.date():
                    if attempt.score > leaderboard.last_daily_score:
                        leaderboard.last_daily_score = attempt.score
                else:
                    leaderboard.last_daily_score = attempt.score
                    leaderboard.last_daily_update = now.date()

                leaderboard.save()

        return Response({
            "type": "success",
            "message": "Tournament attempt submitted successfully.",
            "data": {
                "attempt_id": attempt.id,
                "final_score": attempt.score,
                "correct_answers": correct,
                "wrong_answers": wrong,
                "skipped_questions": skipped,
                "time_taken_seconds": attempt.time_taken_seconds,
                "leaderboard_score_updated": leaderboard.total_score
            }
        }, status=status.HTTP_200_OK)
        
        
class AllActiveTournamentLeaderboards(APIView):
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):

        active_tournaments = Tournament.objects.filter(status="active")

        result = []

        for t in active_tournaments:
            attempts = TournamentAttempt.objects.filter(tournament=t)

            user_scores = defaultdict(
                lambda: {
                    "total_score": 0,
                    "attempts": 0,
                    "first_attempt_date": None,
                    "user_obj": None
                }
            )

            # Aggregate attempt data
            for attempt in attempts:
                user_obj = attempt.user or attempt.guest_user
                if not user_obj:
                    continue

                uid = f"user_{user_obj.id}"

                user_scores[uid]["total_score"] += attempt.score
                user_scores[uid]["attempts"] += 1
                user_scores[uid]["user_obj"] = user_obj

                # Track earliest attempt time
                if user_scores[uid]["first_attempt_date"] is None:
                    user_scores[uid]["first_attempt_date"] = attempt.attempt_date
                else:
                    user_scores[uid]["first_attempt_date"] = min(
                        user_scores[uid]["first_attempt_date"],
                        attempt.attempt_date
                    )

            # Sorting logic
            sorted_list = sorted(
                user_scores.values(),
                key=lambda x: (
                    -x["total_score"],
                    x["attempts"],
                    x["first_attempt_date"]
                )
            )

            # Add ranks
            leaderboard = []
            for idx, entry in enumerate(sorted_list, start=1):
                user_obj = entry["user_obj"]

                leaderboard.append({
                    "userId": user_obj.id,
                    "userName": getattr(user_obj, "username", "Anonymous"),
                    "rank": idx,
                    "total_score": entry["total_score"],
                    "attempts": entry["attempts"],
                    "first_attempt_date": entry["first_attempt_date"]
                })

            # Append tournament leaderboard
            result.append({
                "tournament_id": t.id,
                "title": t.title,
                "leaderboard": leaderboard
            })

        return Response({
            "type": "success",
            "message": "Active tournament leaderboards fetched.",
            "data": {
                "active_tournaments": result
            }
        }, status=200)



# class AllActiveTournamentLeaderboards(APIView):
#     authentication_classes = [CombinedJWTOrGuestAuthentication]
#     permission_classes = [AllowAny]

#     def get(self, request, *args, **kwargs):

#         active_tournaments = Tournament.objects.filter(status="active")

#         result = []

#         for t in active_tournaments:

#             # -----------------------------------
#             # (1) TOURNAMENT LEADERBOARD
#             # -----------------------------------

#             attempts = TournamentAttempt.objects.filter(
#                 tournament=t
#             ).select_related("user", "guest_user")

#             user_scores = defaultdict(
#                 lambda: {
#                     "total_score": 0,
#                     "attempts": 0,
#                     "first_attempt_date": None,
#                     "user_obj": None
#                 }
#             )

#             for attempt in attempts:
#                 user_obj = attempt.user or attempt.guest_user
#                 if not user_obj:
#                     continue

#                 uid = f"user_{user_obj.id}"

#                 user_scores[uid]["total_score"] += attempt.score
#                 user_scores[uid]["attempts"] += 1
#                 user_scores[uid]["user_obj"] = user_obj

#                 # Track earliest attempt time
#                 if user_scores[uid]["first_attempt_date"] is None:
#                     user_scores[uid]["first_attempt_date"] = attempt.attempt_date
#                 else:
#                     user_scores[uid]["first_attempt_date"] = min(
#                         user_scores[uid]["first_attempt_date"],
#                         attempt.attempt_date
#                     )

#             # Sorting logic
#             sorted_list = sorted(
#                 user_scores.values(),
#                 key=lambda x: (
#                     -x["total_score"],     # high score wins
#                     x["attempts"],         # fewer attempts is better
#                     x["first_attempt_date"]  # earlier is better
#                 )
#             )

#             tournament_leaderboard = []
#             for idx, entry in enumerate(sorted_list, start=1):
#                 user_obj = entry["user_obj"]

#                 tournament_leaderboard.append({
#                     "userId": user_obj.id,
#                     "userName": getattr(user_obj, "username", "Anonymous"),
#                     "rank": idx,
#                     "total_score": entry["total_score"],
#                     "attempts": entry["attempts"],
#                     "first_attempt_date": entry["first_attempt_date"]
#                 })

#             # -----------------------------------
#             # (2) WORD PUZZLE LEADERBOARDS
#             # -----------------------------------

#             word_puzzle_leaderboards = []

#             # Only get puzzles connected to the tournament
#             puzzles = WordPuzzle.objects.filter(
#                 tournament=t
#             )

#             for p in puzzles:

#                 puzzle_attempts = WordPuzzleAttempt.objects.filter(
#                     puzzle=p
#                 ).select_related("user", "guest")

#                 puzzle_scores = defaultdict(
#                     lambda: {
#                         "correct": 0,
#                         "attempts": 0,
#                         "user_obj": None
#                     }
#                 )

#                 for att in puzzle_attempts:
#                     user_obj = att.user or att.guest
#                     if not user_obj:
#                         continue

#                     uid = f"user_{user_obj.id}"

#                     if att.is_correct:
#                         puzzle_scores[uid]["correct"] += 1

#                     puzzle_scores[uid]["attempts"] += 1
#                     puzzle_scores[uid]["user_obj"] = user_obj

#                 # Sorting: more correct answers first, fewer attempts better
#                 sorted_puzzle_scores = sorted(
#                     puzzle_scores.values(),
#                     key=lambda x: (
#                         -x["correct"],
#                         x["attempts"],
#                     )
#                 )

#                 puzzle_board = []
#                 for idx, entry in enumerate(sorted_puzzle_scores, start=1):
#                     user_obj = entry["user_obj"]

#                     puzzle_board.append({
#                         "userId": user_obj.id,
#                         "userName": getattr(user_obj, "username", "Anonymous"),
#                         "rank": idx,
#                         "correct": entry["correct"],
#                         "attempts": entry["attempts"],
#                     })

#                 word_puzzle_leaderboards.append({
#                     "puzzle_id": p.id,
#                     "title": p.title,
#                     "leaderboard": puzzle_board
#                 })

#             # Add everything to the tournament
#             result.append({
#                 "tournament_id": t.id,
#                 "title": t.title,
#                 "leaderboard": tournament_leaderboard,
#                 "word_puzzle_leaderboards": word_puzzle_leaderboards
#             })

#         return Response({
#             "type": "success",
#             "message": "Active tournament leaderboards fetched.",
#             "data": {
#                 "active_tournaments": result
#             }
#         }, status=200)


class SubmitTournamentPuzzleAPIView(APIView):
    """
    Submit answers for a tournament puzzle one by one.
    """
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]  # Adjust if only logged-in users allowed

    def post(self, request, *args, **kwargs):
        tournament_id = request.data.get("tournament_id")
        puzzle_id = request.data.get("puzzle_id")
        word_id = request.data.get("word_id")
        user_answer = request.data.get("answer")
        time_taken = request.data.get("time_taken", 0)

        if not all([tournament_id, puzzle_id, word_id, user_answer]):
            return Response({"error": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        # ---------------------------
        # Step 1: Authenticate user or guest
        # ---------------------------
        user = None
        guest_user = None

        try:
            auth_result = CombinedJWTOrGuestAuthentication().authenticate(request)
            if auth_result:
                user_or_guest, _ = auth_result
                if hasattr(user_or_guest, 'is_authenticated') and user_or_guest.is_authenticated:
                    user = user_or_guest
                else:
                    guest_user = user_or_guest
        except Exception as e:
            return Response({"error": f"Authentication failed: {str(e)}"}, status=status.HTTP_401_UNAUTHORIZED)

        # ---------------------------
        # Step 2: Validate tournament and puzzle
        # ---------------------------
        tournament = get_object_or_404(Tournament, id=tournament_id)
        puzzle = get_object_or_404(WordPuzzle, id=puzzle_id, tournaments=tournament)

        # ---------------------------
        # Step 3: Get or create puzzle attempt
        # ---------------------------
        attempt, created = TournamentPuzzleAttempt.objects.get_or_create(
            tournament=tournament,
            wordPuzzle=puzzle,
            defaults={
                "user": user,
                "guest_user": guest_user,
                "total_words": puzzle.words.count(),
            }
        )

        # Ensure ownership
        if not created:
            if user and attempt.user != user:
                return Response({"error": "This puzzle attempt belongs to another user."}, status=400)
            if guest_user and attempt.guest_user != guest_user:
                return Response({"error": "This puzzle attempt belongs to another guest."}, status=400)

        # ---------------------------
        # Step 4: Check the word
        # ---------------------------
        word = get_object_or_404(Word, id=word_id, puzzle=puzzle)
        is_correct = word.text.strip().lower() == user_answer.strip().lower()

        if is_correct:
            attempt.correct_words += 1
        else:
            attempt.wrong_words += 1

        attempt.time_taken += int(time_taken)

        # ---------------------------
        # Step 5: Check if puzzle completed
        # ---------------------------
        if attempt.correct_words + attempt.wrong_words >= attempt.total_words:
            attempt.is_completed = True

        # Score calculation
        attempt.score = attempt.correct_words
        attempt.save()

        # ---------------------------
        # Step 6: Determine next word
        # ---------------------------
        next_word = None
        if not attempt.is_completed:
            answered_ids = request.data.get("answered_ids", [])
            remaining_words = puzzle.words.exclude(id__in=answered_ids)
            if remaining_words.exists():
                next_word_obj = remaining_words.first()
                next_word = {
                    "id": next_word_obj.id,
                    "text_hint": next_word_obj.hint,
                    "difficulty": next_word_obj.difficulty
                }

        # ---------------------------
        # Step 7: Response
        # ---------------------------
        return Response({
            "type": "success",
            "message": "Word submitted successfully.",
            "data": {
                "is_correct": is_correct,
                "correct_words": attempt.correct_words,
                "wrong_words": attempt.wrong_words,
                "skipped_words": attempt.skipped_words,
                "score": attempt.score,
                "is_completed": attempt.is_completed,
                "next_word": next_word
            }
        }, status=200)