from django.contrib import admin
from .models import WordPuzzle, Word, PuzzleAttempt, WordAttempt


# ---------------------------------
# Word Inline (inside Puzzle)
# ---------------------------------
class WordInline(admin.TabularInline):
    model = Word
    extra = 1
    fields = ("text", "hint", "difficulty", "created_at")
    readonly_fields = ("created_at",)


# ---------------------------------
# WordPuzzle Admin
# ---------------------------------
class WordPuzzleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "start_date",
        "end_date",
        "created_at"
    )
    list_filter = ("status",)
    search_fields = ("title",)
    inlines = [WordInline]
    readonly_fields = ("created_at",)


# ---------------------------------
# WordAttempt Inline (inside PuzzleAttempt)
# ---------------------------------
class WordAttemptInline(admin.TabularInline):
    model = WordAttempt
    extra = 0
    fields = (
        "word",
        "is_correct",
        "attempts_count",
        "time_taken",
        "created_at"
    )
    readonly_fields = ("created_at",)


# ---------------------------------
# PuzzleAttempt Admin
# ---------------------------------
class PuzzleAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_or_guest",
        "puzzle",
        "total_attempts",
        "correct_words",
        "total_time_taken",
        "is_completed",
        "started_at",
        "finished_at",
    )

    list_filter = (
        "is_completed",
        "puzzle",
        "started_at",
    )

    search_fields = (
        "user__email",
        "guest__id",
        "puzzle__title",
    )

    readonly_fields = (
        "started_at",
        "finished_at",
        "total_time_taken",
        "created_at",
    )

    inlines = [WordAttemptInline]

    def user_or_guest(self, obj):
        if obj.user:
            return obj.user.email
        elif obj.guest:
            return f"Guest({obj.guest.id})"
        return "-"
    user_or_guest.short_description = "User/Guest"


# ---------------------------------
# WordAttempt Admin (optional separate view)
# ---------------------------------
class WordAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "puzzle_attempt",
        "word",
        "is_correct",
        "attempts_count",
        "time_taken",
        "created_at",
    )

    list_filter = ("is_correct", "word")
    search_fields = ("word__text",)
    readonly_fields = ("created_at",)


# ---------------------------------
# Register models
# ---------------------------------
admin.site.register(WordPuzzle, WordPuzzleAdmin)
admin.site.register(PuzzleAttempt, PuzzleAttemptAdmin)
admin.site.register(WordAttempt, WordAttemptAdmin)