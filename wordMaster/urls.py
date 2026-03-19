from django.urls import path, include
from .views import *

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'admin/word-puzzles', WordPuzzleAdminViewSet, basename='admin-wordpuzzle')

urlpatterns = [
    
    path('api/', include(router.urls)),

    # -----------------------------------------
    # 1️⃣ GET All Active Puzzles
    # -----------------------------------------
    path(
        "api/puzzles/",
        PuzzleListView.as_view(),
        name="puzzle-list"
    ),

    # -----------------------------------------
    # 2️⃣ START Puzzle (Create Attempt)
    # -----------------------------------------
    path(
        "api/puzzles/start/",
        StartPuzzleView.as_view(),
        name="start-puzzle"
    ),
    
    path(
        "api/puzzles/upload-words-excel/",
        UploadWordsExcelAPIView.as_view(),
        name="upload_words_excel"
    ),

    # -----------------------------------------
    # 3️⃣ GET Next Word (by Attempt ID)
    # -----------------------------------------
    # path(
    #     "api/puzzle-attempt/<int:attempt_id>/word/",
    #     PuzzleWordView.as_view(),
    #     name="puzzle-word"
    # ),

    # -----------------------------------------
    # 4️⃣ Submit Word Answer
    # -----------------------------------------
    path(
        "api/puzzle-attempt/submit/",
        SubmitPuzzleAllAnswersView.as_view(),
        name="submit-puzzle-answer"
    ),

    # -----------------------------------------
    # 5️⃣ Finish Puzzle
    # -----------------------------------------
    path(
        "api/puzzle-attempt/<int:attempt_id>/finish/",
        FinishPuzzleView.as_view(),
        name="finish-puzzle"
    ),

    # -----------------------------------------
    # 6️⃣ Get User Puzzle Summary
    # -----------------------------------------
    path(
        "api/puzzles/<int:puzzle_id>/summary/",
        PuzzleUserSummaryView.as_view(),
        name="puzzle-summary"
    ),
    
    
    path(
        "api/puzzles/leaderboard/",
        PuzzleLeaderboardView.as_view(),
        name="puzzle-leaderboard"
    )
]



### rewards endpoints



urlpatterns += [

    path(
        "api/rewards/calculate/",
        CalculateRewardAPIView.as_view()
    ),

    # path(
    #     "api/rewards/my-points/",
    #     MyPointsAPIView.as_view()
    # ),

    path(
        "api/rewards/history/",
        RewardHistoryAPIView.as_view()
    ),

    path(
        "api/rewards/leaderboard/",
        LeaderboardAPIView.as_view()
    ),

    path(
        "api/rewards/claim/",
        ClaimRewardAPIView.as_view()
    ),

]


