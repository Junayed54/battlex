from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, get_user_model
from rest_framework.views import APIView
from .serializers import *
from quiz.models import *
from .models import *
from tournaments.models import *
from django.db.models import Sum, F, Window
from django.db.models.functions import Rank

User = get_user_model()

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def get_client_ip(self, request):
        """Extract IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "type": "error",
                    "message": "User with this email already exists.",
                    "data": {}
                },
                status=status.HTTP_200_OK,
            )

        user = serializer.save()

        # Get IP address
        client_ip = self.get_client_ip(request)

        # Get guest accounts with matching IP
        guest_users = UserOpenAccount.objects.filter(ip_address=client_ip, user__isnull=True)

        for guest_user in guest_users:
            guest_user.user = user
            guest_user.status = "active"
            guest_user.save()

            # Transfer data
            QuizAttempt.objects.filter(guest_user=guest_user, user__isnull=True).update(user=user)
            UserActivityLog.objects.filter(user=guest_user, user__isnull=True).update(user=guest_user)

        return Response(
            {
                "type": "success",
                "message": "User registered successfully",
                "data": {
                    "data": UserSerializer(user).data
                }
            },
            status=status.HTTP_200_OK,
        )
        



class UserLoginView(generics.GenericAPIView):
    """
    API view for user login.
    """
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "type": "error",
                    "message": "Invalid credentials",
                    "data": {}
                },
                status=status.HTTP_200_OK,
            )
        
        return Response(
            {
                "type": "success",
                "message": "Login successful",
                "data":{
                    "data":{
                        "access_token": serializer.validated_data['access_token'],
                        "refresh_token": serializer.validated_data['refresh_token']
                    }
                } 
            },
            status=status.HTTP_200_OK,
        )
        
        
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Allow admins to view all users; regular users only see their own data.
        """
        if self.request.user.is_staff:
            return super().get_queryset()
        return User.objects.filter(id=self.request.user.id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "type": "success",
                "message": "Users retrieved successfully",
                "data": {
                    "data":serializer.data
                } 
            },
            status=status.HTTP_200_OK,
        )
        


from rest_framework.permissions import IsAdminUser

from .models import UserOpenAccount

from .serializers import UserOpenAccountSerializer
class UserOpenAccountViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserOpenAccount.objects.all().order_by("-last_seen_at")
    serializer_class = UserOpenAccountSerializer
    permission_classes = [IsAdminUser] 
    
    

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "type": "success",
            "message": "Profile retrieved successfully",
            "data": {
                "name": getattr(user, "name", ""),
                "email": user.email,
                "profile_image": getattr(user, "profile_picture", None)
            }
        })
        
        
        
# class UserProfileView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         user = request.user

#         # Fetch all attempts made by this user (logged-in user only)
#         attempts = QuizAttempt.objects.filter(user=user)

#         total_score = attempts.aggregate(total=models.Sum("score"))["total"] or 0
#         total_attempts = attempts.count()

#         return Response({
#             "type": "success",
#             "message": "Profile retrieved successfully",
#             "data": {
#                 "name": getattr(user, "name", ""),
#                 "email": user.email,
#                 "profile_image": getattr(user, "profile_picture", None),

#                 # ✔️ Added statistics
#                 "total_attempts": total_attempts,
#                 "total_score": total_score,
#             }
#         })




class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # --- Overall User Stats (Using Tournament Attempts for consistency, assuming QuizAttempt is related to another app) ---
        # If QuizAttempt is the correct source for overall stats, keep your original logic for total_score/total_attempts
        # Otherwise, use TournamentAttempt:
        all_attempts = TournamentAttempt.objects.filter(user=user)
        total_score = all_attempts.aggregate(total=Sum("score"))["total"] or 0
        total_attempts = all_attempts.count()

        # --- Active Tournament Stats ---
        
        # 1. Get all active tournaments
        # Note: The custom manager should automatically update the status when the queryset is accessed.
        active_tournaments = Tournament.objects.filter(status='active').prefetch_related('attempts')
        
        tournament_stats = []
        
        for tournament in active_tournaments:
            # 2. Get the current user's total score for this specific tournament
            user_tournament_score = tournament.attempts.filter(user=user).aggregate(
                total_score=Sum('score')
            )['total_score'] or 0

            # 3. Calculate all participants' total scores for this tournament
            # We group by the user who made the attempt and sum their scores.
            leaderboard_data = TournamentAttempt.objects.filter(
                tournament=tournament,
                is_completed=True # Only consider completed attempts for the leaderboard
            ).values('user').annotate(
                total_score=Sum('score')
            ).order_by('-total_score')
            
            # Find the user's rank in the aggregated list
            user_rank = None
            
            # Simple ranking implementation (iterating through the data)
            current_rank = 0
            previous_score = None
            
            for i, entry in enumerate(leaderboard_data):
                # Handle ties by keeping the same rank for the same score
                if previous_score is None or entry['total_score'] < previous_score:
                    current_rank = i + 1
                
                if entry['user'] == user.id:
                    user_rank = current_rank
                    break
                
                previous_score = entry['total_score']
            
            tournament_stats.append({
                'id': tournament.id,
                'name': tournament.title,
                'user_score': user_tournament_score,
                'user_rank': user_rank or 'N/A' # N/A if user has no completed attempts
            })


        # 4. Construct the Final Response
        return Response({
            "type": "success",
            "message": "Profile and Tournament Stats retrieved successfully",
            "data": {
                "name": getattr(user, "name", ""),
                "email": user.email,
                "profile_image": getattr(user, "profile_picture", None),

                # # Overall statistics
                # "total_attempts": total_attempts,
                # "total_score": total_score,
                
                # Active Tournament Stats
                "tournaments": tournament_stats
            }
        })