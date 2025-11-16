from django.contrib import admin
from .models import Tournament, TournamentPrize, TournamentWinner, TournamentAttempt, TournamentLeaderboard

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'frequency', 'status', 'start_date', 'end_date', 'max_questions_per_attempt', 'duration_minutes')
    list_filter = ('frequency', 'status', 'start_date')
    search_fields = ('title', 'description')
    date_hierarchy = 'start_date'
    fieldsets = (
        (None, {
            'fields': ('title', 'description')
        }),
        ('Schedule', {
            'fields': ('frequency', 'start_date', 'end_date', 'status')
        }),
        ('Rules', {
            'fields': ('max_questions_per_attempt', 'max_attempts_per_day', 'max_total_attempts', 'duration_minutes', 'negative_marking')
        }),
        ('Questions', {
            'fields': ('questions',)
        }),
    )
    filter_horizontal = ('questions',)
    ordering = ['-start_date']

@admin.register(TournamentPrize)
class TournamentPrizeAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'prize_type', 'rank', 'title', 'value')
    list_filter = ('tournament', 'prize_type')
    search_fields = ('title', 'description', 'tournament__title')
    fieldsets = (
        (None, {
            'fields': ('tournament', 'prize_type', 'rank')
        }),
        ('Prize Details', {
            'fields': ('title', 'description', 'value')
        }),
    )
    ordering = ['tournament', 'prize_type', 'rank']

@admin.register(TournamentWinner)
class TournamentWinnerAdmin(admin.ModelAdmin):
    list_display = ('get_participant', 'tournament', 'prize', 'winning_score', 'winning_rank', 'award_date', 'claim_status')
    list_filter = ('tournament', 'claim_status', 'award_date')
    search_fields = ('tournament__title', 'prize__title', 'user__email', 'guest_user__id')
    fieldsets = (
        (None, {
            'fields': ('tournament', 'prize')
        }),
        ('Winner Details', {
            'fields': ('user', 'guest_user', 'winning_score', 'winning_rank', 'claim_status')
        }),
    )
    readonly_fields = ('award_date',)
    ordering = ['-award_date']

    def get_participant(self, obj):
        return obj.user.email if obj.user else obj.guest_user.id if obj.guest_user else "N/A"
    get_participant.short_description = 'Participant'

@admin.register(TournamentAttempt)
class TournamentAttemptAdmin(admin.ModelAdmin):
    list_display = ('get_participant', 'tournament', 'score', 'correct_answers', 'wrong_answers', 'skipped_questions', 'attempt_date', 'is_completed')
    list_filter = ('tournament', 'is_completed', 'attempt_date')
    search_fields = ('tournament__title', 'user__email', 'guest_user__id')
    fieldsets = (
        (None, {
            'fields': ('tournament', 'user', 'guest_user')
        }),
        ('Attempt Details', {
            'fields': ('score', 'correct_answers', 'wrong_answers', 'skipped_questions', 'questions_attempted', 'time_taken_seconds', 'is_completed')
        }),
    )
    filter_horizontal = ('questions_attempted',)
    readonly_fields = ('attempt_date', 'end_time')
    ordering = ['-attempt_date']

    def get_participant(self, obj):
        return obj.user.email if obj.user else obj.guest_user.id if obj.guest_user else "N/A"
    get_participant.short_description = 'Participant'

@admin.register(TournamentLeaderboard)
class TournamentLeaderboardAdmin(admin.ModelAdmin):
    list_display = ('get_participant', 'tournament', 'total_score', 'last_daily_score', 'last_attempt_datetime')
    list_filter = ('tournament',)
    search_fields = ('tournament__title', 'user__email', 'guest_user__id')
    fieldsets = (
        (None, {
            'fields': ('tournament', 'user', 'guest_user')
        }),
        ('Scores', {
            'fields': ('total_score', 'last_daily_score', 'last_daily_update', 'last_attempt_datetime')
        }),
    )
    readonly_fields = ('last_daily_update', 'last_attempt_datetime')
    ordering = ['-total_score']

    def get_participant(self, obj):
        return obj.user.email if obj.user else obj.guest_user.id if obj.guest_user else "N/A"
    get_participant.short_description = 'Participant'