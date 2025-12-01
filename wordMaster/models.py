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


class WordPuzzleAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    guest = models.ForeignKey(
        UserOpenAccount,
        to_field="id",          # Important: tells Django FK uses CharField primary key
        db_column="guest_id",   # Make sure DB column matches
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    puzzle = models.ForeignKey(WordPuzzle, on_delete=models.CASCADE)
    word = models.ForeignKey(Word, on_delete=models.CASCADE)

    is_correct = models.BooleanField(default=False)
    attempts_count = models.PositiveIntegerField(default=1)
    time_taken = models.PositiveIntegerField(default=0)  # in seconds (optional)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        who = self.user.email if self.user else f"Guest({self.guest_id})"
        status = "Correct" if self.is_correct else "Wrong"
        return f"{who} - {self.word.text} ({status})"



