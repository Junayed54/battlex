# tournaments/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import *
from quiz.models import Question, Option # Assuming your quiz app models

User = get_user_model()

class TournamentQuestionUploadSerializer(serializers.Serializer):
    """
    Serializer for validating the tournament ID and the uploaded Excel file.
    """
    tournament_id = serializers.PrimaryKeyRelatedField(
        queryset=Tournament.objects.all(),
        source='tournament', # Map to 'tournament' in validated_data
        help_text="ID of the tournament to which questions will be added."
    )
    excel_file = serializers.FileField(
        help_text="Excel file (.xlsx) containing questions and options."
    )

    def validate_excel_file(self, value):
        if not value.name.endswith('.xlsx'):
            raise serializers.ValidationError("Invalid file type. Only .xlsx Excel files are allowed.")
        return value
    
    
    
class TournamentPrizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TournamentPrize
        fields = ['id', 'prize_type', 'rank', 'title', 'description', 'value']

class TournamentSerializer(serializers.ModelSerializer):
    prizes = TournamentPrizeSerializer(many=True, read_only=True)
    # questions = QuestionSerializer(many=True, read_only=True) # Optional: if you want to embed all questions in tournament list/detail

    class Meta:
        model = Tournament
        fields = [
            'id', 'title', 'subtitle', 'description', 'banner_image', 'frequency', 'start_date', 'end_date',
            'max_total_attempts', 'max_questions_per_attempt', 'max_attempts_per_day',
            'negative_marking', 'duration_minutes', 'status', 'prizes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at', 'status') # Admins might change status

class TournamentAttemptSerializer(serializers.ModelSerializer):
    # This will display the user's email or guest ID in read-only mode
    user_identifier = serializers.SerializerMethodField()
    tournament_title = serializers.CharField(source='tournament.title', read_only=True)
    
    class Meta:
        model = TournamentAttempt
        fields = [
            'id', 'user', 'guest_user', 'user_identifier', 'tournament', 'tournament_title',
            'score', 'correct_answers', 'wrong_answers', 'skipped_questions',
            'attempt_date', 'end_time', 'time_taken_seconds', 'is_completed'
        ]
        read_only_fields = [
            'user', 'guest_user', 'score', 'correct_answers', 'wrong_answers',
            'skipped_questions', 'attempt_date', 'end_time', 'time_taken_seconds',
            'is_completed', 'questions_attempted' # questions_attempted is managed internally
        ]

    def get_user_identifier(self, obj):
        if obj.user:
            return obj.user.email # Or obj.user.username
        elif obj.guest_user:
            return f"Guest-{obj.guest_user.id}"
        return "N/A"

    # For creating an attempt, only tournament_id is needed, user/guest are set by view
    def create(self, validated_data):
        # The user/guest_user will be set by the view based on request context
        # This serializer mostly focuses on validating the tournament
        return super().create(validated_data)


class TournamentLeaderboardSerializer(serializers.ModelSerializer):
    user_identifier = serializers.SerializerMethodField()
    tournament_title = serializers.CharField(source='tournament.title', read_only=True)

    class Meta:
        model = TournamentLeaderboard
        fields = [
            'id', 'user', 'guest_user', 'user_identifier', 'tournament', 'tournament_title',
            'total_score', 'last_daily_score', 'last_daily_update', 'last_attempt_datetime'
        ]
        read_only_fields = fields # Leaderboard entries are managed by system, not directly created/updated via API by user

    def get_user_identifier(self, obj):
        if obj.user:
            return obj.user.email
        elif obj.guest_user:
            return f"Guest-{obj.guest_user.id}"
        return "N/A"

class TournamentWinnerSerializer(serializers.ModelSerializer):
    user_identifier = serializers.SerializerMethodField()
    tournament_title = serializers.CharField(source='tournament.title', read_only=True)
    prize_details = TournamentPrizeSerializer(source='prize', read_only=True)

    class Meta:
        model = TournamentWinner
        fields = [
            'id', 'tournament', 'tournament_title', 'prize', 'prize_details',
            'user', 'guest_user', 'user_identifier', 'winning_score',
            'winning_rank', 'award_date', 'claim_status'
        ]
        read_only_fields = fields # Winners are recorded by system, not directly created/updated via API

    def get_user_identifier(self, obj):
        if obj.user:
            return obj.user.email
        elif obj.guest_user:
            return f"Guest-{obj.guest_user.id}"
        return "N/A"

class StartTournamentAttemptSerializer(serializers.Serializer):
    tournament_id = serializers.CharField(help_text="ID of the tournament to start an attempt for.")

    def validate_tournament_id(self, value):
        try:
            tournament_id = int(value)
        except (ValueError, TypeError):
            raise serializers.ValidationError("Tournament ID must be an integer or numeric string.")

        try:
            tournament = Tournament.objects.get(
                pk=tournament_id,
                status='active',
                end_date__gte=timezone.now()
            )
        except Tournament.DoesNotExist:
            raise serializers.ValidationError(
                f"Tournament with ID '{value}' does not exist or is not active."
            )
        
        return tournament

    def validate(self, attrs):
        # Assign the validated tournament instance to the attrs
        attrs['tournament'] = attrs.pop('tournament_id')  # override original key
        return attrs
    
    

class AnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option_id = serializers.IntegerField()

class SubmitTournamentAttemptSerializer(serializers.Serializer):
    attempt_id = serializers.PrimaryKeyRelatedField(
        queryset=TournamentAttempt.objects.filter(is_completed=False),
        help_text="The ID of the tournament attempt being submitted."
    )
    answers = AnswerSerializer(many=True, help_text="List of question answers including question_id and selected_option_id.")
