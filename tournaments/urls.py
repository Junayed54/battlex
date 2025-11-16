# tournaments/urls.py
from django.urls import path
from . import views # Your regular views
from .views import * # Your DRF view

urlpatterns = [
    
    path('api/tournaments/upload-questions/', TournamentQuestionUploadAPIView.as_view(), name='api_tournament_question_upload'),
    
    path('api/tournaments/', views.TournamentListView.as_view(), name='api-tournament-list'),
    path('api/tournaments/<int:pk>/', views.TournamentDetailView.as_view(), name='api-tournament-detail'),
    
    path('api/tournaments/<int:tournament_id>/prizes/', views.TournamentPrizeListView.as_view(), name='api-tournament-prize-list'),
    path('api/tournaments/<int:tournament_id>/winners/', views.TournamentWinnerListView.as_view(), name='api-tournament-winner-list'),
    path('api/tournaments/<int:tournament_id>/leaderboard/', views.TournamentLeaderboardListView.as_view(), name='api-tournament-leaderboard'),

    # --- User API Views ---
    path('api/tournaments/user-attempts/', views.UserTournamentAttemptListView.as_view(), name='api-user-attempts'),

    # --- Attempt Actions (Start & Submit) ---
    path('api/tournaments/start/', views.StartTournamentAttemptView.as_view(), name='api-start-attempt'),
    path('api/tournaments/submit/', views.SubmitTournamentAttemptView.as_view(), name='api-submit-attempt'),

    # --- Admin API Views ---
    path('api/admin/tournaments/', views.AdminTournamentListCreateView.as_view(), name='api-admin-tournament-list-create'),
    path('api/admin/tournaments/<int:pk>/', views.AdminTournamentDetailView.as_view(), name='api-admin-tournament-detail'),

    path('api/admin/tournaments/<int:tournament_id>/prizes/', views.AdminTournamentPrizeListCreateView.as_view(), name='api-admin-prize-list-create'),
    path('api/admin/tournaments/prizes/<int:prize_id>/', views.AdminTournamentPrizeDetailView.as_view(), name='api-admin-prize-detail'),

    path('api/admin/tournaments/winners/', views.AdminTournamentWinnerListView.as_view(), name='api-admin-winner-list'),
]