from django.db import models
from django.contrib.auth import get_user_model
from users.models import *

User = get_user_model()

class WordPuzzle(models.Model):
    title = models.CharField(max_length=200)
    banner = models.ImageField(upload_to="puzzle_banners/", null=True, blank=True)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("upcoming", "Upcoming"), ("ended", "Ended")],
        default="active"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Word(models.Model):
    puzzle = models.ForeignKey(WordPuzzle, on_delete=models.CASCADE, related_name="words")

    text = models.CharField(max_length=100)       # original word
    hint = models.CharField(max_length=200, blank=True, null=True)

    difficulty = models.CharField(
        max_length=20,
        choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")],
        default="easy"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text} ({self.difficulty})"
    
    
    
    
class PuzzleAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest = models.ForeignKey(
        UserOpenAccount,
        to_field="id",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    puzzle = models.ForeignKey(WordPuzzle, on_delete=models.CASCADE)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    total_attempts = models.PositiveIntegerField(default=0)
    correct_words = models.PositiveIntegerField(default=0)

    # ⏱️ Total time taken (nullable)
    total_time_taken = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total time in seconds"
    )

    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_time(self):
        if self.started_at and self.finished_at:
            return int((self.finished_at - self.started_at).total_seconds())
        return None

    def __str__(self):
        if self.user:
            return f"{self.user.email} - {self.puzzle.title}"
        return f"Guest({self.guest_id}) - {self.puzzle.title}"
    
    

class WordAttempt(models.Model):
    puzzle_attempt = models.ForeignKey(
        PuzzleAttempt,
        on_delete=models.CASCADE,
        related_name="word_attempts"
    )

    word = models.ForeignKey(Word, on_delete=models.CASCADE)

    is_correct = models.BooleanField(default=False)

    attempts_count = models.PositiveIntegerField(default=1)

    # ⏱️ Time taken for this word (nullable)
    time_taken = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Time in seconds for this word"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "Correct" if self.is_correct else "Wrong"
        return f"{self.word.text} ({status})"