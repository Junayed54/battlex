from django.urls import path
from .views import *

urlpatterns = [
    path('api/quiz/create/', QuizCreateAPIView.as_view(), name='create-quiz'),
    path('api/category/create/', CategoryCreateAPIView.as_view(), name='create-category'),
    path('api/item/create/', ItemCreateAPIView.as_view(), name='create-item'),
    path("api/category/update/<int:pk>/", CategoryPartialUpdateAPIView.as_view(), name="category-update"),
    path("api/item/update/<int:pk>/", ItemPartialUpdateAPIView.as_view(), name="item-update"),
    path('api/upload-questions/', QuestionUploadView.as_view(), name='upload-questions'), 
    path('api/quiz/get-questions/', GetQuestionsView.as_view(), name='get-questions'),
    path('api/quiz/submit-answer/', SubmitAnswersView.as_view(), name='submit_answer'),
    # path('quiz/question/', GetQuestionView.as_view(), name='get_question'),  # For the first question
    # path('quiz/question/<int:question_id>/', GetQuestionView.as_view(), name='get_next_question'),
    # path('get-question/<int:question_id>/', GetQuestionView.as_view(), name='get-question'),
    path('api/quiz/dashboard/', DashboardView.as_view(), name='dashboard'),
]
