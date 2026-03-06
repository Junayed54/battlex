from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from .models import WordPuzzle, Word, PuzzleAttempt, WordAttempt
from .serializers import *
import random
from users.models import UserOpenAccount


# --------------------------------------------------------
# Helper: Get Authenticated User or Guest
# --------------------------------------------------------
def get_request_user(request):
    """Return (user, guest) tuple."""
    if request.user and request.user.is_authenticated:
        return request.user, None

    open_id = request.data.get("open_account_id") or request.query_params.get("open_account_id")
    if not open_id:
        return None, None

    guest, _ = UserOpenAccount.objects.get_or_create(id=open_id)
    return None, guest


# --------------------------------------------------------
# 1. GET PUZZLE LIST
# --------------------------------------------------------
class PuzzleListView(APIView):
    def get(self, request):
        puzzles = WordPuzzle.objects.filter(status="active")
        return Response({
            "type": "success",
            "message": "Puzzle list loaded successfully",
            "data": PuzzleSerializer(puzzles, many=True).data
        })
        
        
# --------------------------------------------------------
# 2. START PUZZLE
# --------------------------------------------------------
class StartPuzzleView(APIView):

    def post(self, request, puzzle_id):
        user, guest = get_request_user(request)
        puzzle = get_object_or_404(WordPuzzle, id=puzzle_id)

        # Prevent multiple active attempts
        existing_attempt = PuzzleAttempt.objects.filter(
            puzzle=puzzle,
            is_completed=False
        ).filter(
            Q(user=user) | Q(guest=guest)
        ).first()

        if existing_attempt:
            return Response({
                "type": "success",
                "message": "Existing attempt resumed",
                "data": {"attempt_id": existing_attempt.id}
            })

        attempt = PuzzleAttempt.objects.create(
            user=user,
            guest=guest,
            puzzle=puzzle
        )

        return Response({
            "type": "success",
            "message": "Puzzle started",
            "data": {"attempt_id": attempt.id}
        })
        
# --------------------------------------------------------
# 4. SUBMIT ANSWER
# --------------------------------------------------------
class SubmitPuzzleAnswerView(APIView):

    def post(self, request):
        attempt_id = request.data.get("attempt_id")
        word_id = request.data.get("word_id")
        answer = request.data.get("answer", "").strip().lower()
        time_taken = request.data.get("time_taken")  # nullable

        if not attempt_id or not word_id or not answer:
            return Response({
                "type": "error",
                "message": "attempt_id, word_id and answer required",
                "data": {}
            }, status=400)

        attempt = get_object_or_404(PuzzleAttempt, id=attempt_id)
        word = get_object_or_404(Word, id=word_id)

        is_correct = (answer == word.text.lower())

        WordAttempt.objects.create(
            puzzle_attempt=attempt,
            word=word,
            is_correct=is_correct,
            attempts_count=1,
            time_taken=time_taken if time_taken else None
        )

        # Update PuzzleAttempt stats
        attempt.total_attempts += 1
        if is_correct:
            attempt.correct_words += 1
        attempt.save()

        return Response({
            "type": "success",
            "message": "Answer submitted",
            "data": {
                "is_correct": is_correct
            }
        })
        
        
# --------------------------------------------------------
# 5. FINISH PUZZLE
# --------------------------------------------------------
class FinishPuzzleView(APIView):

    def post(self, request, attempt_id):
        attempt = get_object_or_404(PuzzleAttempt, id=attempt_id)

        if attempt.is_completed:
            return Response({
                "type": "error",
                "message": "Already completed",
                "data": {}
            })

        attempt.finished_at = timezone.now()
        attempt.total_time_taken = int(
            (attempt.finished_at - attempt.started_at).total_seconds()
        )
        attempt.is_completed = True
        attempt.save()

        return Response({
            "type": "success",
            "message": "Puzzle completed",
            "data": {
                "total_attempts": attempt.total_attempts,
                "correct_words": attempt.correct_words,
                "total_time_seconds": attempt.total_time_taken
            }
        })
        


# --------------------------------------------------------
# 6. USER PUZZLE SUMMARY
# --------------------------------------------------------
class PuzzleUserSummaryView(APIView):

    def get(self, request, puzzle_id):
        user, guest = get_request_user(request)
        puzzle = get_object_or_404(WordPuzzle, id=puzzle_id)

        attempts = PuzzleAttempt.objects.filter(
            puzzle=puzzle,
            is_completed=True
        ).filter(
            Q(user=user) | Q(guest=guest)
        )

        if not attempts.exists():
            return Response({
                "type": "success",
                "message": "No attempts found",
                "data": {}
            })

        best_attempt = attempts.order_by("-correct_words", "total_time_taken").first()

        return Response({
            "type": "success",
            "message": "Puzzle summary",
            "data": {
                "total_attempts": best_attempt.total_attempts,
                "correct_words": best_attempt.correct_words,
                "total_time_seconds": best_attempt.total_time_taken
            }
        })
        
        
class PuzzleLeaderboardView(APIView):
    
    def get(self, request, puzzle_id):
        puzzle = get_object_or_404(WordPuzzle, id=puzzle_id)

        leaderboard = (
            PuzzleAttempt.objects
            .filter(puzzle=puzzle, is_completed=True)
            .order_by("-correct_words", "total_time_taken")
        )

        data = []
        rank = 1

        for attempt in leaderboard:
            player_name = None

            if attempt.user:
                player_name = attempt.user.username or attempt.user.email
            elif attempt.guest:
                player_name = f"Guest-{attempt.guest_id}"

            data.append({
                "rank": rank,
                "player": player_name,
                "correct_words": attempt.correct_words,
                "total_attempts": attempt.total_attempts,
                "total_time_seconds": attempt.total_time_taken
            })

            rank += 1

        return Response({
            "type": "success",
            "message": "Leaderboard loaded",
            "data": data
        })