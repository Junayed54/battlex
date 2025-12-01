from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import WordPuzzle, Word, WordPuzzleAttempt
from .serializers import *
import random
from users.models import *


def get_request_user(request):
    """Return (user, guest) tuple."""
    if request.user.is_authenticated:
        return request.user, None

    # Guest system
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
# 2. GET NEXT PUZZLE WORD (One by One)
# --------------------------------------------------------
class PuzzleWordView(APIView):

    def get(self, request, puzzle_id):
        user, guest = get_request_user(request)
        puzzle = get_object_or_404(WordPuzzle, id=puzzle_id)

        # Get all words
        words = list(Word.objects.filter(puzzle=puzzle))

        if not words:
            return Response({"type": "error", "message": "No words found", "data": []}, status=404)

        # Option 1: Random word every time (unlimited)
        word = random.choice(words)

        return Response({
            "type": "success",
            "message": "Next puzzle word loaded",
            "data": {
                "word_id": word.id,
                "text": word.text,
                "hint": word.hint,
                "difficulty": word.difficulty
            }
        })


# --------------------------------------------------------
# 3. SUBMIT ANSWER
# --------------------------------------------------------
class SubmitPuzzleAnswerView(APIView):

    def post(self, request):
        user, guest = get_request_user(request)
        word_id = request.data.get("word_id")
        answer = request.data.get("answer", "").strip().lower()
        time_taken = request.data.get("time_taken", 0)

        if not word_id or not answer:
            return Response({"type": "error", "message": "word_id and answer required", "data": {}}, status=400)

        word = get_object_or_404(Word, id=word_id)
        is_correct = (answer.lower() == word.text.lower())

        attempt = WordPuzzleAttempt.objects.create(
            user=user,
            guest=guest,
            puzzle=word.puzzle,
            word=word,
            is_correct=is_correct,
            attempts_count=1,
            time_taken=time_taken
        )

        return Response({
            "type": "success",
            "message": "Answer submitted",
            "data": {
                "word_id": word.id,
                "is_correct": is_correct,
                "attempt_id": attempt.id
            }
        })


# --------------------------------------------------------
# 4. USER PUZZLE SUMMARY
# --------------------------------------------------------
class PuzzleUserSummaryView(APIView):
    def get(self, request, puzzle_id):
        user, guest = get_request_user(request)
        puzzle = get_object_or_404(WordPuzzle, id=puzzle_id)

        attempts = WordPuzzleAttempt.objects.filter(
            puzzle=puzzle,
            user=user if user else None,
            guest=guest if guest else None
        )

        total = attempts.count()
        correct = attempts.filter(is_correct=True).count()
        wrong = total - correct

        return Response({
            "type": "success",
            "message": "Puzzle summary",
            "data": {
                "total_attempts": total,
                "correct": correct,
                "wrong": wrong
            }
        })
