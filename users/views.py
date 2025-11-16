from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import authenticate, get_user_model

from .serializers import UserSerializer, UserRegistrationSerializer, UserLoginSerializer
from quiz.models import *
from .models import *
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
            UserActivityLog.objects.filter(user=guest_user).update(user=guest_user)

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