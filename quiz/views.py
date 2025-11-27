from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from rest_framework.permissions import AllowAny
import pandas as pd
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import AccessToken
from collections import defaultdict
from users.middleware import CombinedJWTOrGuestAuthentication 
from .models import *
from .serializers import *
from users.models import *
import uuid

from tournaments.models import *


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import AuthenticationFailed
import jwt
from jwt.exceptions import InvalidTokenError
from django.conf import settings
import datetime

class QuizCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = QuizSerializer(data=request.data)
        if serializer.is_valid():
            quiz = serializer.save()
            quiz.calculate_total_questions()  # Calculate total questions after saving
            return Response(
                {
                    "type": "success",
                    "message": "Quiz created successfully",
                    "data": {
                        "quiz": serializer.data,
                    }
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "type": "error",
                "message": "Invalid data provided",
                "data": {
                    "quiz": serializer.errors,
                }
            },
            status=status.HTTP_200_OK,
        )

        
        
        
class CategoryCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Deserialize the data
        serializer = CategorySerializer(data=request.data)
        
        # Check if the data is valid
        if serializer.is_valid():
            category = serializer.save()  # Save the category
            return Response({
                "type": "success",
                "message": "Category created successfully",
                "data": {
                    "category": serializer.data,
                }
            }, status.HTTP_200_OK)
        
        # If invalid, return errors with the same response format
        return Response({
            "type": "error",
            "message": "Category creation failed.",
            "data": {
                "category": serializer.errors,
            }
        }, status=status.HTTP_200_OK)



class CategoryPartialUpdateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({
                "type": "error",
                "message": "Category not found."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = CategorySerializer(category, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                "type": "success",
                "message": "Category updated successfully",
                "data": {
                    "data": serializer.data,
                }
            }, status=status.HTTP_200_OK)

        return Response({
            "type": "error",
            "message": "Category update failed.",
            "data": {
                "category": serializer.errors,
            }
        }, status=status.HTTP_400_BAD_REQUEST)


class ItemCreateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Deserialize the data for Item creation
        serializer = ItemSerializer(data=request.data)
        
        # Check if the data is valid
        if serializer.is_valid():
            item = serializer.save()  # Save the item
            return Response(
                {
                    "type": "success",
                    "message": "Item created successfully",
                    "data": {
                        "item": serializer.data,
                    }
                },
                status=status.HTTP_200_OK
            )
        
        # If invalid, return errors with the same structure
        return Response(
            {
                "type": "error",
                "message": "Invalid data provided",
                "data": {
                    "item": serializer.errors,
                }
            },
            status=status.HTTP_200_OK
        )


class ItemPartialUpdateAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            item = Item.objects.get(pk=pk)
        except Item.DoesNotExist:
            return Response({
                "type": "error",
                "message": "Item not found."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = ItemSerializer(item, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                "type": "success",
                "message": "Item updated successfully",
                "data": {
                    "item": serializer.data,
                }
            }, status=status.HTTP_200_OK)

        return Response({
            "type": "error",
            "message": "Item update failed.",
            "data": {
                "item": serializer.errors,
            }
        }, status=status.HTTP_400_BAD_REQUEST)

    
class GetQuestionsView(APIView):
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        category_id = request.data.get('category_id')
        item_id = request.data.get('item_id')
        current_question_index = int(request.data.get('current_question_index', 0))

        # ✅ Manual token validation
        user = None
        guest_user = None

        if hasattr(request, "user") and request.user:
            if getattr(request.user, "is_guest", False):
                guest_user = request.user
            elif isinstance(request.user, User):
                user = request.user
            else:
                return Response({
                    "type": "error",
                    "message": "Invalid or missing token.",
                    "data": {}
                }, status=status.HTTP_200_OK)
        else:
            return Response({
                "type": "error",
                "message": "Authentication credentials were not provided.",
                "data": {}
            }, status=status.HTTP_200_OK)

        # ✅ Get category and item
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return Response({
                "type": "error",
                "message": "Category not found.",
                "data": {}
            }, status=status.HTTP_200_OK)

        try:
            item = Item.objects.get(id=item_id, category=category)
        except Item.DoesNotExist:
            return Response({
                "type": "error",
                "message": "Item not found in this category.",
                "data": {}
            }, status=status.HTTP_200_OK)

        questions = item.questions.all()
        if not questions.exists():
            return Response({
                "type": "error",
                "message": "No questions linked to this item.",
                "data": {}
            }, status=status.HTTP_200_OK)

        if current_question_index < 0 or current_question_index >= questions.count():
            return Response({
                "type": "error",
                "message": "Invalid question index.",
                "data": {}
            }, status=status.HTTP_200_OK)

        question = questions[current_question_index]
        options = Option.objects.filter(question=question)

        answer_set = [
            {
                "answer_id": str(option.id),
                "answer": option.option_text,
                "is_true": option.is_correct
            }
            for option in options
        ]

        return Response({
            "type": "success",
            "message": "Question fetched successfully.",
            "data": {
                "question": [{
                    "question_id": str(question.id),
                    "question": question.question_text,
                    "answer_set": answer_set
                }],
                "next_question_index": (
                    current_question_index + 1
                    if current_question_index + 1 < questions.count()
                    else None
                ),
                "is_last_question": current_question_index + 1 >= questions.count()
            }
        }, status=status.HTTP_200_OK)








from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from django.utils.timezone import now
import jwt
import uuid

from .models import Quiz, Category, Item, QuizAttempt, Leaderboard
from users.models import UserOpenAccount

def get_client_ip(request):
    """Get client IP address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip





class DashboardView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        user = None
        response_type = "success"
        message = "Dashboard fetched successfully"
        access_token = None
        open_account_id = None

        jwt_auth = JWTAuthentication()
        auth_header = request.headers.get("Authorization", "")

        # Step 1: Authenticate user
        try:
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, _ = auth_result
                if auth_header.startswith("Bearer "):
                    access_token = auth_header.split(" ")[1]
        except AuthenticationFailed:
            pass

        # Step 2: Check guest token manually if no user
        if not user and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                decoded = jwt.decode(token, settings.SIMPLE_JWT['SIGNING_KEY'], algorithms=["HS256"])
                if decoded.get("is_guest"):
                    open_account_id = decoded.get("open_account_id")
                    access_token = token  # reuse existing token
            except jwt.ExpiredSignatureError:
                message = "Guest token expired."
                return Response({"type": "error", "message": message, "data": {}}, status=200)
            except jwt.InvalidTokenError:
                message = "Invalid token."
                return Response({"type": "error", "message": message, "data": {}}, status=200)

        # Step 3: Create guest open_account and token if none
        if not user and not access_token:
            client_ip = get_client_ip(request)
            open_account = UserOpenAccount.objects.filter(ip_address=client_ip, user__isnull=True).first()
            if open_account:
                open_account_id = str(open_account.id)
            else:
                open_account_id = str(uuid.uuid4())
                open_account = UserOpenAccount.objects.create(
                    id=open_account_id,
                    ip_address=client_ip,
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )
            guest_token = AccessToken()
            guest_token.set_exp(lifetime=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'])
            guest_token["is_guest"] = True
            guest_token["open_account_id"] = open_account_id
            access_token = str(guest_token)

        # Build quizzes data (your existing logic)
        quizzes = Quiz.objects.all()
        quiz_data = []
        for quiz in quizzes:
            categories = Category.objects.filter(quiz=quiz)
            filtered_categories = []
            for category in categories:
                if category.access_mode == "private" and (not user or not getattr(user, "is_authenticated", False)):
                    continue

                items = Item.objects.filter(category=category)
                filtered_items = []
                for item in items:
                    if item.access_mode == "private" and (not user or not getattr(user, "is_authenticated", False)):
                        continue

                    quiz_attempt_data = None
                    if user and getattr(user, "is_authenticated", False):
                        quiz_attempt = QuizAttempt.objects.filter(user=user, item=item).first()
                        if quiz_attempt:
                            quiz_attempt_data = {
                                "total_questions": quiz_attempt.total_questions,
                                "correct_answers": quiz_attempt.correct_answers,
                                "wrong_answers": quiz_attempt.wrong_answers,
                                "score": quiz_attempt.score,
                            }

                    leaderboard_data = Leaderboard.objects.filter(item=item).order_by('-score')[:10]
                    leaderboard = [
                        {
                            "user": entry.user.username,
                            "score": entry.score,
                            "rank": entry.rank,
                        }
                        for entry in leaderboard_data
                    ]

                    filtered_items.append({
                        "item_id": str(item.id),
                        "item_title": item.title,
                        "item_subtitle": item.subtitle,
                        "item_button_label": item.button_label or "Play",
                        "access_mode": item.access_mode or "public",
                        "item_type": item.item_type or "default",
                        "quiz_attempt": quiz_attempt_data,
                        "leaderboard": leaderboard,
                    })

                if filtered_items:
                    filtered_categories.append({
                        "category_id": str(category.id),
                        "category_title": category.title,
                        "category_type": category.category_type or "default",
                        "access_mode": category.access_mode,
                        "task_items": filtered_items,
                    })

            quiz_data.append({
                "quiz_id": str(quiz.id),
                "quiz_title": quiz.title,
                "quiz_description": quiz.description,
                "total_questions": quiz.total_questions,
                "created_at": quiz.created_at,
                "updated_at": quiz.updated_at,
                "categories": filtered_categories,
            })

        # Add tournaments data here
        # tournaments = Tournament.objects.filter(end_date__gte=timezone.now()).order_by('-start_date')
        tournaments = Tournament.objects.all().order_by('-start_date')

        tournaments_data = []
        for tournament in tournaments:
            tournaments_data.append({
                "id": str(tournament.id),
                "title": tournament.title,
                "start_date": tournament.start_date,
                "end_date": tournament.end_date,
                "status": tournament.status
                # Add any other fields you want to expose
            })

        return Response(
            {
                "type": response_type,
                "message": message,
                "data": {
                    "quizzes": quiz_data,
                    "tournaments": tournaments_data,
                    "access_token": access_token,
                },
            },
            status=200,
        )





class QuestionUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response(
                {
                    "type": "error",
                    "message": "No file uploaded.",
                    "data": {},
                },
                status=status.HTTP_200_OK
            )

        try:
            df = pd.read_excel(file)

            # Normalize column names
            df.columns = [col.lower() for col in df.columns]
            required_columns = [
                'question', 'subject', 'category', 'options_num',
                'option1', 'option2', 'option3', 'option4', 'answer'
            ]

            if not all(col in df.columns for col in required_columns):
                return Response(
                    {
                        "type": "error",
                        "message": "Excel file is missing required columns.",
                        "data": {},
                    },
                    status=status.HTTP_200_OK
                )

            with transaction.atomic():
                for _, row in df.iterrows():
                    row_lower = {k.lower(): v for k, v in row.items()}

                    category_id = str(row_lower.get('category')).strip() if not pd.isna(row_lower.get('category')) else None
                    subject_id = str(row_lower.get('subject')).strip() if not pd.isna(row_lower.get('subject')) else None
                    question_text = str(row_lower.get('question')).strip() if not pd.isna(row_lower.get('question')) else None
                    options_num = int(row_lower.get('options_num')) if not pd.isna(row_lower.get('options_num')) else 0
                    answer_field = str(row_lower.get('answer')).strip() if not pd.isna(row_lower.get('answer')) else ""

                    try:
                        category = Category.objects.get(id=category_id)
                    except Category.DoesNotExist:
                        return Response(
                            {
                                "type": "error",
                                "message": f"Category with ID {category_id} not found.",
                                "data": {},
                            },
                            status=status.HTTP_200_OK
                        )

                    item = Item.objects.filter(id=subject_id, category=category).first()
                    if not item:
                        return Response(
                            {
                                "type": "error",
                                "message": f"Item with ID {subject_id} in Category {category.title} not found.",
                                "data": {},
                            },
                            status=status.HTTP_200_OK
                        )

                    question= Question.objects.create(question_text=question_text)
                    item.questions.add(question)

                    # Extract options
                    options = []
                    i = 1
                    while True:
                        option_col = f'option{i}'.lower()
                        option_text = row_lower.get(option_col)
                        if pd.isna(option_text):
                            break
                        options.append(str(option_text).strip())
                        i += 1

                    # Normalize answers from mixed format
                    raw_answers = [str(a).strip().lower() for a in answer_field.split(',') if str(a).strip()]
                    parsed_answers = []
                    for ans in raw_answers:
                        if ans.startswith('option') and ans[6:].isdigit():
                            idx = int(ans[6:]) - 1
                            if 0 <= idx < len(options):
                                parsed_answers.append(options[idx].capitalize())
                        else:
                            parsed_answers.append(ans.capitalize())

                    # Save options
                    for option_text in options:
                        is_correct = option_text.capitalize() in parsed_answers
                        Option.objects.update_or_create(
                            question=question,
                            option_text=option_text.capitalize(),
                            defaults={'is_correct': is_correct}
                        )


            return Response(
                {
                    "type": "success",
                    "message": "Questions uploaded successfully!",
                    "data": {},
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {
                    "type": "error",
                    "message": str(e),
                    "data": {},
                },
                status=status.HTTP_200_OK
            )




        
        


class SubmitAnswersView(APIView):
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]  # Manual check

    def post(self, request, *args, **kwargs):
        item_id = request.data.get("item_id")
        answers = request.data.get("answers", [])
        start_fresh = request.data.get("start_fresh", False)

        try:
            item = Item.objects.get(id=item_id)
            quiz = item.category.quiz
        except Item.DoesNotExist:
            return Response({"type": "error", "message": "Invalid item.", "data": {}}, status=200)

        negative_marking = quiz.negative_marking

        if not request.user:
            return Response({"type": "error", "message": "Authentication required."}, status=200)

        if isinstance(request.user, User):
            user = request.user
            guest_user = None
        elif isinstance(request.user, UserOpenAccount):
            user = None
            guest_user = request.user
        else:
            return Response({"type": "error", "message": "Invalid user."}, status=200)

        # Create or get QuizAttempt
        filters = {"item": item}
        if user:
            filters["user"] = user
        else:
            filters["guest_user"] = guest_user

        if start_fresh:
            quiz_attempt = QuizAttempt.objects.create(user=user, guest_user=guest_user, item=item, total_questions=item.questions.count())
        else:
            quiz_attempt = QuizAttempt.objects.filter(**filters).order_by("-attempt_date").first()
            if not quiz_attempt or (quiz_attempt.correct_answers + quiz_attempt.wrong_answers == quiz_attempt.total_questions):
                quiz_attempt = QuizAttempt.objects.create(user=user, guest_user=guest_user, item=item, total_questions=item.questions.count())

        # Process Answers
        result_data = []
        for answer in answers:
            question_id = answer.get("question_id")
            selected_option_ids = answer.get("selected_option_ids", [])

            try:
                question = Question.objects.get(id=question_id)
            except Question.DoesNotExist:
                continue

            correct_options = set(Option.objects.filter(question=question, is_correct=True).values_list("id", flat=True))
            selected_set = set(selected_option_ids)

            is_correct = selected_set == correct_options

            if is_correct:
                quiz_attempt.correct_answers += 1
                quiz_attempt.score += 1
            else:
                quiz_attempt.wrong_answers += 1
                quiz_attempt.score -= negative_marking

            result_data.append({
                "question_id": question_id,
                "is_correct": is_correct,
                "selected_options": list(selected_set),
                "correct_options": list(correct_options),
            })

        quiz_attempt.save()

        return Response({
            "type": "success",
            "message": "Answers submitted successfully.",
            "data": {
                "results": result_data,
                "score": quiz_attempt.score,
                "correct_answers": quiz_attempt.correct_answers,
                "wrong_answers": quiz_attempt.wrong_answers,
                "total_questions": quiz_attempt.total_questions,
                "quiz_completed": (quiz_attempt.correct_answers + quiz_attempt.wrong_answers == quiz_attempt.total_questions),
            },
        }, status=200)




class ItemLeaderboardView(APIView):
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, item_id, *args, **kwargs):
        # Determine if the requesting user is authenticated
        is_authenticated = request.user.is_authenticated

        # Fetch the item
        try:
            item = Item.objects.get(id=item_id)
        except Item.DoesNotExist:
            return Response({
                "type": "error",
                "message": "Invalid item.",
                "data": {}
            }, status=200)

        # Fetch all attempts for this item
        attempts_qs = QuizAttempt.objects.filter(item=item)

        # Aggregate scores per user (or guest_user)
        user_scores = defaultdict(lambda: {"total_score": 0, "attempts": 0, "first_attempt_date": None})

        for attempt in attempts_qs:
            user_obj = attempt.user or attempt.guest_user
            if not user_obj:
                continue

            user_id = user_obj.id

            user_scores[user_id]["total_score"] += attempt.score
            user_scores[user_id]["attempts"] += 1
            if user_scores[user_id]["first_attempt_date"] is None:
                user_scores[user_id]["first_attempt_date"] = attempt.attempt_date
            else:
                # Keep the earliest attempt date
                user_scores[user_id]["first_attempt_date"] = min(user_scores[user_id]["first_attempt_date"], attempt.attempt_date)

            user_scores[user_id]["user_obj"] = user_obj

        # Sort leaderboard
        leaderboard_list = sorted(
            user_scores.values(),
            key=lambda x: (-x["total_score"], x["attempts"], x["first_attempt_date"])
        )

        # Add rank
        final_leaderboard = []
        for idx, entry in enumerate(leaderboard_list, start=1):
            user_obj = entry["user_obj"]
            final_leaderboard.append({
                "userId": user_obj.id,
                "userName": user_obj.username if is_authenticated and hasattr(user_obj, "username") else "Anonymous",
                "rank": idx,
                "total_score": entry["total_score"],
                "attempts": entry["attempts"],
                "first_attempt_date": entry["first_attempt_date"]
            })

        return Response({
            "type": "success",
            "message": "Leaderboard fetched successfully.",
            "data": {
                "item_id": item_id,
                "leaderboard": final_leaderboard
            }
        }, status=200)
        
       
 
class AllItemLeaderboardView(APIView):
    authentication_classes = [CombinedJWTOrGuestAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        is_authenticated = request.user.is_authenticated
        print("hello")
        all_items = Item.objects.all()
        final_data = []

        for item in all_items:
            attempts_qs = QuizAttempt.objects.filter(item=item)

            user_scores = defaultdict(lambda: {
                "total_score": 0,
                "attempts": 0,
                "first_attempt_date": None,
                "user_obj": None
            })

            # Aggregate data
            for attempt in attempts_qs:
                user_obj = attempt.user or attempt.guest_user
                if not user_obj:
                    continue

                user_id = user_obj.id
                entry = user_scores[user_id]

                entry["total_score"] += attempt.score
                entry["attempts"] += 1

                if entry["first_attempt_date"] is None:
                    entry["first_attempt_date"] = attempt.attempt_date
                else:
                    entry["first_attempt_date"] = min(
                        entry["first_attempt_date"], 
                        attempt.attempt_date
                    )

                entry["user_obj"] = user_obj

            # Sort the leaderboard for this item
            leaderboard_list = sorted(
                user_scores.values(),
                key=lambda x: (-x["total_score"], x["attempts"], x["first_attempt_date"])
            )

            # Add rank
            formatted_lb = []
            for idx, entry in enumerate(leaderboard_list, start=1):
                user_obj = entry["user_obj"]

                formatted_lb.append({
                    "userId": user_obj.id,
                    "userName": user_obj.username if is_authenticated and hasattr(user_obj, "username") else "Anonymous",
                    "rank": idx,
                    "total_score": entry["total_score"],
                    "attempts": entry["attempts"],
                    "first_attempt_date": entry["first_attempt_date"]
                })

            final_data.append({
                "item_id": item.id,
                "item_title": item.title,
                "leaderboard": formatted_lb
            })

        return Response({
            "type": "success",
            "message": "All items leaderboard fetched successfully.",
            "data": final_data
        }, status=200)