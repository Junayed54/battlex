from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import *

# Create a router for the UserViewSet
router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register(r"users/activity", UserOpenAccountViewSet, basename="user-activity")


urlpatterns = [
    # User registration endpoint
    path('api/user/register/', UserRegistrationView.as_view(), name='user-register'),
    # User login endpoint
    path('api/user/login/', UserLoginView.as_view(), name='user-login'),
    # Include the router URLs for the UserViewSet
    path('', include(router.urls)),
]


urlpatterns += [
    path("api/", include(router.urls)),
    path("api/user/profile/", UserProfileView.as_view(), name="user-profile"),

]