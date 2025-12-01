from django.contrib import admin
from .models import WordPuzzle, Word, WordPuzzleAttempt

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
    list_display = ("title", "status", "start_date", "end_date", "created_at")
    list_filter = ("status",)
    search_fields = ("title",)
    inlines = [WordInline]


# ---------------------------------
# WordPuzzleAttempt Admin
# ---------------------------------
class WordPuzzleAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_or_guest",
        "puzzle",
        "word",
        "is_correct",
        "attempts_count",
        "time_taken",
        "created_at"
    )
    list_filter = ("is_correct", "puzzle", "word")
    search_fields = ("user__email", "guest__id", "puzzle__title", "word__text")
    readonly_fields = ("created_at",)

    def user_or_guest(self, obj):
        if obj.user:
            return obj.user.email
        elif obj.guest:
            return f"Guest({obj.guest.id})"
        return "-"
    user_or_guest.short_description = "User/Guest"


# ---------------------------------
# Register models
# ---------------------------------
admin.site.register(WordPuzzle, WordPuzzleAdmin)
admin.site.register(WordPuzzleAttempt, WordPuzzleAttemptAdmin)
