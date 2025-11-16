from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
from users.models import UserOpenAccount
class Quiz(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    total_questions = models.PositiveIntegerField(default=0)
    negative_marking = models.FloatField(
        default=0, 
        help_text="Specify the negative marking value for incorrect answers. Default is 0 (no negative marking)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def calculate_total_questions(self):
        """Calculate the total number of questions in the quiz and return the value."""
        total_questions = 0
        for category in self.categories.all():  # Access categories related to the quiz
            for item in category.items.all():  # Access items related to the category
                total_questions += item.questions.count()  # Count questions in each item
        return total_questions or 0

class Category(models.Model):
    title = models.CharField(max_length=200)
    category_type = models.CharField(max_length=100, choices=[
        ('default', 'Default'),
        ('regular_quiz', 'Regular Quiz'),
        ('practice', 'Practice'),
        ('reading', 'Reading'),
    ])
    quiz = models.ForeignKey(Quiz, related_name='categories', on_delete=models.CASCADE)
    access_mode = models.CharField(max_length=50, choices=[
        ('public', 'Public'),
        ('private', 'Private'),
    ], default='public')
    
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.quiz:
            self.quiz.calculate_total_questions()
    def __str__(self):
        return self.title


class Item(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    button_label = models.CharField(max_length=50, default='Play')
    access_mode = models.CharField(max_length=50, choices=[
        ('public', 'Public'),
        ('private', 'Private'),
    ], default='public')
    item_type = models.CharField(max_length=100)
    category = models.ForeignKey(Category, related_name='items', on_delete=models.CASCADE)
    questions = models.ManyToManyField('Question', related_name='items')  # <-- this line added

    def __str__(self):
        return self.title


class Question(models.Model):
    question_text = models.TextField()

    def __str__(self):
        return self.question_text



class Option(models.Model):
    option_text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)

    def __str__(self):
        return self.option_text



class QuizAttempt(models.Model):
    # Allow both authenticated users and guest users
    user = models.ForeignKey(
        User,  # This will link to the 'User' model, which can either be a regular user or a guest user
        on_delete=models.CASCADE,
        null=True,  # Null because guest users won't always be authenticated
        blank=True  # Allow blank for guest users
    )
    guest_user = models.ForeignKey(
        UserOpenAccount,  # This links to the guest user model
        on_delete=models.CASCADE,
        null=True,  # Null because regular users won't always have a guest user associated
        blank=True  # Allow blank for authenticated users
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)  # Connect with Item
    total_questions = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField(default=0)
    wrong_answers = models.PositiveIntegerField(default=0)
    score = models.FloatField(default=0)
    attempt_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user or self.guest_user} - {self.item.title}"

    def calculate_score(self):
        """ Calculate total score based on correct answers. """
        self.score = self.correct_answers
        self.save()




class Leaderboard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)  # Or Quiz if you want leaderboard at quiz level
    score = models.PositiveIntegerField()
    rank = models.PositiveIntegerField(null=True, blank=True)  # Rank will be set when generating leaderboard
    attempt_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.score} in {self.item.title}"

    class Meta:
        # Optional: You can order the leaderboard by score and attempt date (descending order)
        ordering = ['-score', 'attempt_date']

    def save(self, *args, **kwargs):
        # Update rank based on the score before saving
        self.rank = self.calculate_rank()
        super().save(*args, **kwargs)

    def calculate_rank(self):
        """Calculate the rank based on score and attempt_date."""
        all_scores = Leaderboard.objects.filter(item=self.item).order_by('-score', 'attempt_date')
        rank = 1
        for idx, entry in enumerate(all_scores):
            if entry.user == self.user:
                rank = idx + 1
                break
        return rank
