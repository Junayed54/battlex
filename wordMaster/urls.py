from django.urls import path
from .views import *



urlpatterns = [

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
        "api/puzzles/<int:puzzle_id>/start/",
        StartPuzzleView.as_view(),
        name="start-puzzle"
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
        SubmitPuzzleAnswerView.as_view(),
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
        "api/puzzles/<int:puzzle_id>/leaderboard/",
        PuzzleLeaderboardView.as_view(),
        name="puzzle-leaderboard"
    )
]