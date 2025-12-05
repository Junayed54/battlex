from django.urls import path
from .views import *

urlpatterns = [
    # GET All Puzzles
    path("api/puzzles/", PuzzleListView.as_view(), name="puzzle-list"),

    path('api/puzzles/<int:puzzle_id>/word/', PuzzleWordView.as_view(), name='puzzle-word'),
    # GET Puzzle Details + Words
    # path("api/puzzles/<int:puzzle_id>/", PuzzleDetailView.as_view(), name="puzzle-detail"),

    # POST Submit Attempt for a Word
    path("api/puzzles/submit/", SubmitPuzzleAnswerView.as_view(), name="submit-attempt"),

    # GET Summary for one puzzle (user-specific)
    # path("api/puzzles/<int:puzzle_id>/summary/", PuzzleSummaryView.as_view(), name="puzzle-summary"),
]



