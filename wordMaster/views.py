from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
import pandas as pd

from .models import WordPuzzle, Word, PuzzleAttempt, WordAttempt
from .serializers import *
import random
from users.models import UserOpenAccount

from users.middleware import CombinedJWTOrGuestAuthentication

import jwt
import uuid
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
# --------------------------------------------------------
# Helper: Get Authenticated User or Guest
# --------------------------------------------------------



def get_client_ip(request):
    """Extracts the real IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



def get_request_user(request):
    user = None
    guest = None
    access_token = None
    
    jwt_auth = JWTAuthentication()
    auth_header = request.headers.get("Authorization", "")

    # 1. Try Authenticated User
    try:
        auth_result = jwt_auth.authenticate(request)
        if auth_result:
            user, _ = auth_result
            if auth_header.startswith("Bearer "):
                access_token = auth_header.split(" ")[1]
            return user, None, access_token
    except AuthenticationFailed:
        pass

    # 2. Try Guest JWT
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            decoded = jwt.decode(token, settings.SIMPLE_JWT['SIGNING_KEY'], algorithms=["HS256"])
            if decoded.get("is_guest"):
                guest_uuid = decoded.get("open_account_id")
                guest = UserOpenAccount.objects.filter(uuid=guest_uuid).first()
                if guest:
                    return None, guest, token
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            pass

    # 3. Fallback to IP detection
    
    client_ip = get_client_ip(request)
    
    guest = UserOpenAccount.objects.filter(
        ip_address=client_ip, 
        user__isnull=True,
        status='active'
    ).first()
    
    if not guest:
        guest = UserOpenAccount.objects.create(
            uuid=str(uuid.uuid4()),
            ip_address=client_ip,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
    
    # Create fresh token
    new_token = AccessToken()
    new_token.set_exp(lifetime=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'])
    new_token["is_guest"] = True
    new_token["open_account_id"] = str(guest.uuid)
    access_token = str(new_token)

    return None, guest, access_token


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
        
        
        
class UploadWordsExcelAPIView(APIView):
    
    def post(self, request):
        
        puzzle_id = request.data.get("puzzle_id")
        excel_file = request.FILES.get("file")
        print (puzzle_id)
        if not excel_file:
            return Response(
                {"error": "Excel file is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        puzzle = get_object_or_404(WordPuzzle, id=puzzle_id)

        try:
            df = pd.read_excel(excel_file)

            words_created = []

            for _, row in df.iterrows():

                word = Word.objects.create(
                    puzzle=puzzle,
                    text=str(row.get("text")).strip(),
                    hint=row.get("hint"),
                    difficulty=row.get("difficulty", "easy")
                )

                words_created.append(word.text)

            return Response({
                "message": "Words uploaded successfully",
                "total_words": len(words_created),
                "words": words_created
            })

        except Exception as e:

            return Response({
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# --------------------------------------------------------
# 2. START PUZZLE
# --------------------------------------------------------
class StartPuzzleView(APIView):
    
    def post(self, request):
        puzzle_id = request.data.get("puzzle_id")
        print(puzzle_id)
        user, guest = get_request_user(request)
        puzzle = get_object_or_404(WordPuzzle, id=puzzle_id)

        # existing_attempt = PuzzleAttempt.objects.filter(
        #     puzzle=puzzle,
        #     is_completed=False
        # ).filter(
        #     Q(user=user) | Q(guest=guest)
        # ).first()

        # if existing_attempt:
        #     words = Word.objects.filter(puzzle=puzzle)

        #     return Response({
        #         "type": "success",
        #         "message": "Existing attempt resumed",
        #         "data": {
        #             "attempt_id": existing_attempt.id,
        #             "words": WordSerializer(words, many=True).data
        #         }
        #     })

        # attempt = PuzzleAttempt.objects.create(
        #     user=user,
        #     guest=guest,
        #     puzzle=puzzle
        # )

        word_ids = list(
        Word.objects.filter(puzzle=puzzle)
        .values_list("id", flat=True)
        )

        random_ids = random.sample(word_ids, min(10, len(word_ids)))

        words = Word.objects.filter(id__in=random_ids)

        return Response({
            "type": "success",
            "message": "Puzzle started",
            "data": {
                # "attempt_id": attempt.id,
                "words": WordSerializer(words, many=True).data
            }
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
        


class SubmitPuzzleAllAnswersView(APIView):
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    
    def post(self, request):
        # UPDATED: Added access_token to the unpack logic
        user, guest, access_token = get_request_user(request)
        
        if not user and not guest:
            return Response({
                "type": "error",
                "message": "User or guest required"
            }, status=400)

        puzzle_id = request.data.get("puzzle_id")
        puzzle = get_object_or_404(WordPuzzle, id=puzzle_id)

        answers = request.data.get("answers", [])
        total_time = request.data.get("total_time")

        if not answers or not isinstance(answers, list):
            return Response({"type": "error", "message": "Answers must be a list"}, status=400)

        if total_time is None:
            return Response({"type": "error", "message": "Total time required"}, status=400)

        # Create puzzle attempt
        attempt = PuzzleAttempt.objects.create(
            user=user,
            guest=guest,
            puzzle=puzzle,
            total_time_taken=total_time,
            is_completed=True
        )

        total_correct = 0
        total_attempts = 0

        for item in answers:
            word_id = item.get("word_id")
            answer = item.get("answer", "").strip().lower()

            if not word_id or not answer:
                continue

            word = get_object_or_404(Word, id=word_id)
            is_correct = (answer == word.text.lower())

            WordAttempt.objects.create(
                puzzle_attempt=attempt,
                word=word,
                is_correct=is_correct,
                attempts_count=1
            )

            total_attempts += 1
            if is_correct:
                total_correct += 1

        attempt.total_attempts = total_attempts
        attempt.correct_words = total_correct
        attempt.save()

        return Response({
            "type": "success",
            "message": "Puzzle completed",
            # "access_token": access_token,  # UPDATED: Return the token to frontend
            "data": {
                "total_answers": total_attempts,
                "correct_words": total_correct,
                "total_time_seconds": total_time
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
        
        
from django.db.models import Max, Min, Q

class PuzzleLeaderboardView(APIView):
    def post(self, request): # Changed to post if sending puzzle_id in body
        puzzle_id = request.data.get("puzzle_id")
        puzzle = get_object_or_404(WordPuzzle, id=puzzle_id)

        # 1. Group by user AND guest to get the best score for each unique player
        # We find the Max correct words and Min time taken for those correct words
        leaderboard_queryset = (
            PuzzleAttempt.objects.filter(puzzle=puzzle)
            .values('user__email', 'user__name', 'guest__uuid') # Grouping keys
            .annotate(
                best_score=Max('correct_words'),
                best_time=Min('total_time_taken')
            )
            .order_by("-best_score", "best_time")
        )

        data = []
        for rank, entry in enumerate(leaderboard_queryset, start=1):
            # Determine the display name
            if entry['user__email']:
                player_name = entry['user__name'] or entry['user__email']
            else:
                # Show first 8 chars of UUID for guests
                player_name = f"Guest-{entry['guest__uuid'][:8]}" if entry['guest__uuid'] else "Unknown"

            data.append({
                "rank": rank,
                "player": player_name,
                "correct_words": entry['best_score'],
                "total_time_seconds": entry['best_time']
            })

        return Response({
            "type": "success",
            "message": "Leaderboard loaded",
            "data": data
        })
        
        
        
        
### rewards part

from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

class CalculateRewardAPIView(APIView):

    def post(self, request):

        attempt_id = request.data.get("attempt_id")

        attempt = get_object_or_404(PuzzleAttempt, id=attempt_id)

        rules = RewardRule.objects.filter(is_active=True)

        total_points = 0

        for rule in rules:

            if rule.rule_type == "correct_word":
                total_points += attempt.correct_words * rule.points

            elif rule.rule_type == "puzzle_complete":
                if attempt.is_completed:
                    total_points += rule.points

            elif rule.rule_type == "speed_bonus":
                if attempt.total_time_taken and rule.max_time_seconds:
                    if attempt.total_time_taken <= rule.max_time_seconds:
                        total_points += rule.points

        RewardEvent.objects.create(
            user=attempt.user,
            guest=attempt.guest,
            puzzle_attempt=attempt,
            points=total_points,
            reason="Puzzle reward"
        )

        balance, created = UserRewardBalance.objects.get_or_create(
            user=attempt.user,
            guest=attempt.guest
        )

        balance.add_points(total_points)

        return Response({
            "points_earned": total_points
        })
        
        
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

class CalculateRewardAPIView(APIView):

    def post(self, request):

        attempt_id = request.data.get("attempt_id")

        attempt = get_object_or_404(PuzzleAttempt, id=attempt_id)

        rules = RewardRule.objects.filter(is_active=True)

        total_points = 0

        for rule in rules:

            if rule.rule_type == "correct_word":
                total_points += attempt.correct_words * rule.points

            elif rule.rule_type == "puzzle_complete":
                if attempt.is_completed:
                    total_points += rule.points

            elif rule.rule_type == "speed_bonus":
                if attempt.total_time_taken and rule.max_time_seconds:
                    if attempt.total_time_taken <= rule.max_time_seconds:
                        total_points += rule.points

        RewardEvent.objects.create(
            user=attempt.user,
            guest=attempt.guest,
            puzzle_attempt=attempt,
            points=total_points,
            reason="Puzzle reward"
        )

        balance, created = UserRewardBalance.objects.get_or_create(
            user=attempt.user,
            guest=attempt.guest
        )

        balance.add_points(total_points)

        return Response({
            "points_earned": total_points
        })
        

class RewardHistoryAPIView(APIView):
    
    def get(self, request):

        rewards = RewardEvent.objects.filter(
            user=request.user
        ).order_by("-created_at")

        serializer = RewardEventSerializer(rewards, many=True)

        return Response(serializer.data)
    
    
    
class LeaderboardAPIView(APIView):
    
    def get(self, request):

        players = UserRewardBalance.objects.order_by(
            "-total_points"
        )[:50]

        data = []

        for p in players:

            data.append({
                "user": p.user.username if p.user else "Guest",
                "points": p.total_points
            })

        return Response(data)
    
    
    


class ClaimRewardAPIView(APIView):
    
    def post(self, request):

        points = int(request.data.get("points"))

        balance = get_object_or_404(
            UserRewardBalance,
            user=request.user
        )

        if balance.total_points < points:

            return Response({
                "error": "Not enough points"
            })

        amount = points / 100

        RewardClaim.objects.create(
            user=request.user,
            points_used=points,
            amount=amount
        )

        balance.subtract_points(points)

        return Response({
            "message": "Reward claim created",
            "amount": amount
        })