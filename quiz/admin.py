from django.contrib import admin
from .models import Quiz, Category, Item, Question, Option, QuizAttempt, Leaderboard

# Register the Option model inline for the Question model
class OptionInline(admin.TabularInline):
    model = Option
    extra = 1  # To show one empty row for adding options

# Custom admin for Question model
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text',)
    inlines = [OptionInline]
    search_fields = ['question_text'] 


# Custom admin for Item model
class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'button_label', 'access_mode', 'item_type', 'category')
    search_fields = ('title', 'subtitle', 'item_type')
    filter_horizontal = ('questions',)  # To filter related questions easily

# Custom admin for Quiz model
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'total_questions', 'negative_marking', 'created_at', 'updated_at')
    search_fields = ('title',)
    readonly_fields = ('total_questions',)  # Make total_questions field readonly
    list_filter = ('created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        # Automatically calculate total_questions before saving
        obj.total_questions = obj.calculate_total_questions()
        super().save_model(request, obj, form, change)

# Custom admin for Category model
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'category_type', 'quiz', 'access_mode')
    list_filter = ('category_type', 'access_mode')
    search_fields = ('title',)

# Custom admin for QuizAttempt model
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'item', 'total_questions', 'correct_answers', 'wrong_answers', 'score', 'attempt_date')
    list_filter = ('attempt_date', 'user')
    search_fields = ('user__username', 'item__title')

# Custom admin for Leaderboard model
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ('user', 'item', 'score', 'rank', 'attempt_date')
    list_filter = ('attempt_date',)
    search_fields = ('user__username', 'item__title')

    def save_model(self, request, obj, form, change):
        # Update the rank before saving the leaderboard entry
        obj.rank = obj.calculate_rank()
        super().save_model(request, obj, form, change)


class OptionAdmin(admin.ModelAdmin):
    list_display =('option_text', 'is_correct')
# Registering the models with the admin site
admin.site.register(Quiz, QuizAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Option, OptionAdmin)
admin.site.register(QuizAttempt, QuizAttemptAdmin)
admin.site.register(Leaderboard, LeaderboardAdmin)
