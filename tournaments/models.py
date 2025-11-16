# tournaments/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone # For timezone.now()

# Assuming UserOpenAccount is in your 'user' app's models.py
# You need to make sure this import path is correct for your project structure
from users.models import UserOpenAccount 

# Assuming Question is in your 'quiz' app's models.py
# You need to make sure this import path is correct for your project structure
from quiz.models import Question 

User = get_user_model() 



class TournamentManager(models.Manager):
    def get_queryset(self):
        # Override the default queryset to include a status update check
        queryset = super().get_queryset()
        
        # Get the current time
        now = timezone.now()

        # Update 'upcoming' tournaments to 'active'
        queryset.filter(status='upcoming', start_date__lte=now).update(status='active')
        
        # Update 'active' tournaments to 'finished'
        queryset.filter(status='active', end_date__lte=now).update(status='finished')
        
        return queryset
    
    
class Tournament(models.Model):
    """
    Defines a single tournament instance with its rules, schedule, and prizes.
    """
    title = models.CharField(max_length=255, help_text="Name of the tournament.")
    subtitle = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Short tagline or subtitle for the tournament."
    )

    description = models.TextField(blank=True, help_text="Detailed description of the tournament.")
    
    
    banner_image = models.ImageField(
        upload_to='tournaments/banners/',
        blank=True,
        null=True,
        help_text="Main banner image representing the tournament."
    )

    # Defines how often the tournament runs or if it's a one-off custom event
    frequency_choices = [
        ('daily', 'Daily'),       # Runs every day
        ('weekly', 'Weekly'),     # Runs every week
        ('monthly', 'Monthly'),   # Runs every month
        ('custom', 'Custom'),     # Admin defines specific start/end dates
    ]
    frequency = models.CharField(
        max_length=50, 
        choices=frequency_choices, 
        default='custom',
        help_text="Defines the recurrence or custom duration of the tournament."
    )
    
    start_date = models.DateTimeField(help_text="The date and time when the tournament begins.")
    end_date = models.DateTimeField(help_text="The date and time when the tournament ends.")
    
    # Pool of questions available for this tournament. Users will draw unique questions from this pool.
    questions = models.ManyToManyField(
        Question, 
        related_name='tournaments', 
        blank=True,
        help_text="The pool of questions from which users will be tested."
    )
    max_total_attempts = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of times a user can attempt the tournament in total. Leave blank for unlimited."
    )
    
    # Rules for user participation
    max_questions_per_attempt = models.PositiveIntegerField(
        default=10, 
        help_text="Maximum number of questions a user will face in a single attempt."
    )
    max_attempts_per_day = models.PositiveIntegerField(
        default=1, 
        help_text="Maximum number of times a user can attempt this tournament in a single day."
    )
    
    # Optional: Negative marking specifically for this tournament
    negative_marking = models.FloatField(
        default=0,
        help_text="Specify the negative marking value for incorrect answers in this tournament. Default is 0."
    )

    # Added: Duration limit for the tournament attempts (in minutes)
    duration_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Maximum time allowed for completing each attempt in minutes (0 for no limit)."
    )

    # Added: Status for the tournament (e.g., upcoming, active, finished, archived)
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('active', 'Active'),
        ('finished', 'Finished'),
        ('archived', 'Archived'),
    ]
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='upcoming',
        help_text="Current administrative status of the tournament."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Use the custom manager
    objects = TournamentManager()

    class Meta:
        verbose_name = "Tournament"
        verbose_name_plural = "Tournaments"
        ordering = ['-start_date', 'title'] # Order by latest starting tournaments
    
    
    
    def save(self, *args, **kwargs):
        """
        Overrides the save method to automatically update the status
        based on the tournament's start and end dates.
        """
        now = timezone.now()
        
        # Check if the tournament should be active
        if self.start_date <= now and self.end_date > now:
            self.status = 'active'
        # Check if the tournament should be finished
        elif self.end_date <= now:
            self.status = 'finished'
        # Otherwise, the tournament is upcoming
        else:
            self.status = 'upcoming'

        # Call the original save() method
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    
    
    
class TournamentPrize(models.Model):
    PRIZE_TYPE_CHOICES = [
        ('daily', 'Daily Prize'),
        ('weekly', 'Weekly Prize'),
        ('overall', 'Overall Prize'),  # renamed from 'final' to make meaning clearer
    ]

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='prizes',
        help_text="The tournament this prize belongs to."
    )

    prize_type = models.CharField(
        max_length=10,
        choices=PRIZE_TYPE_CHOICES,
        help_text="Whether this prize is for daily, weekly, or overall winners."
    )

    rank = models.PositiveIntegerField(
        default=1,
        help_text="Which rank this prize is for (e.g., 1 for first place, 2 for second place)."
    )

    title = models.CharField(
        max_length=255,
        help_text="Name or title of the prize (e.g., Mobile Recharge, Smartwatch)."
    )

    description = models.TextField(
        blank=True,
        help_text="Details about the prize."
    )

    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional monetary value of the prize (e.g., 500.00 for BDT 500)."
    )

    class Meta:
        unique_together = ('tournament', 'prize_type', 'rank')
        ordering = ['prize_type', 'rank']
        verbose_name = "Tournament Prize"
        verbose_name_plural = "Tournament Prizes"

    def __str__(self):
        return f"{self.tournament.title} - {self.get_prize_type_display()} Rank {self.rank}: {self.title}"



# tournaments/models.py

# ... (existing imports and models)

class TournamentWinner(models.Model):
    """
    Records the winner of a specific prize in a tournament.
    This links a user/guest to a prize they have won.
    """
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='winners',
        help_text="The tournament where the prize was won."
    )
    prize = models.ForeignKey(
        TournamentPrize,
        on_delete=models.SET_NULL, # If prize is deleted, winner record might still exist
        null=True,
        blank=True,
        help_text="The specific prize that was awarded."
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="The authenticated user who won the prize (if applicable)."
    )
    guest_user = models.ForeignKey(
        UserOpenAccount,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="The guest user who won the prize (if applicable)."
    )
    winning_score = models.FloatField(
        help_text="The score of the winner at the time of winning the prize."
    )
    winning_rank = models.PositiveIntegerField(
        help_text="The rank of the winner at the time of winning the prize."
    )
    award_date = models.DateTimeField(
        auto_now_add=True,
        help_text="The date and time the prize was awarded/determined."
    )
    # Optional: Status of prize claim (e.g., 'pending', 'claimed', 'distributed')
    claim_status_choices = [
        ('pending', 'Pending Claim'),
        ('claimed', 'Claimed by Winner'),
        ('distributed', 'Prize Distributed'),
        ('unclaimed', 'Unclaimed/Expired'),
    ]
    claim_status = models.CharField(
        max_length=20,
        choices=claim_status_choices,
        default='pending',
        help_text="Status of the prize claim and distribution."
    )

    class Meta:
        verbose_name = "Tournament Winner"
        verbose_name_plural = "Tournament Winners"
        # Prevent awarding the same prize to the same user multiple times for the same tournament
        unique_together = ('tournament', 'prize', 'user', 'guest_user')
        ordering = ['-award_date']
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False, guest_user__isnull=True) |
                      models.Q(user__isnull=True, guest_user__isnull=False),
                name='either_user_or_guest_user_for_winner'
            )
        ]

    def __str__(self):
        participant_name = self.user.email if self.user else (self.guest_user.id if self.guest_user else "N/A")
        return f"{participant_name} won {self.prize.title} in {self.tournament.title}"

class TournamentAttempt(models.Model):
    """
    Records a single attempt by a user (authenticated or guest) in a tournament.
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="The authenticated user who made this attempt (if applicable)."
    )
    guest_user = models.ForeignKey(
        UserOpenAccount, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="The guest user who made this attempt (if applicable)."
    )
    tournament = models.ForeignKey(
        Tournament, 
        on_delete=models.CASCADE, 
        related_name='attempts',
        help_text="The tournament this attempt belongs to."
    )
    
    score = models.FloatField(default=0, help_text="The score achieved in this attempt.")
    correct_answers = models.PositiveIntegerField(default=0, help_text="Number of questions answered correctly.")
    wrong_answers = models.PositiveIntegerField(default=0, help_text="Number of questions answered incorrectly.")
    skipped_questions = models.PositiveIntegerField(default=0, help_text="Number of questions skipped.")
    
    # Stores the specific questions presented to the user in this attempt.
    questions_attempted = models.ManyToManyField(
        Question, 
        related_name='tournament_attempts_by_question',
        help_text="The specific questions presented and attempted in this quiz round."
    )
    
    attempt_date = models.DateTimeField(auto_now_add=True, help_text="The date and time when this attempt was made.")
    
    # Added: End time of the attempt (for timed tournaments)
    end_time = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="The date and time when the attempt was completed/submitted."
    )

    # Added: Total time taken for the attempt (in seconds)
    time_taken_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Total time taken by the user to complete the attempt in seconds (0 if not timed)."
    )

    is_completed = models.BooleanField(
        default=False, 
        help_text="Indicates if the user finished the attempt (true) or abandoned it (false)."
    )

    class Meta:
        verbose_name = "Tournament Attempt"
        verbose_name_plural = "Tournament Attempts"
        ordering = ['-attempt_date'] # Most recent attempts first
        # Constraint to ensure either user or guest_user is set, but not both
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False, guest_user__isnull=True) |
                      models.Q(user__isnull=True, guest_user__isnull=False),
                name='either_user_or_guest_user_for_tournament_attempt'
            )
        ]

    def __str__(self):
        participant = "Unknown"
        if self.user:
            participant = self.user.email # Or self.user.username if you add it
        elif self.guest_user:
            participant = self.guest_user.id
        return f"{participant} - {self.tournament.title} - Score: {self.score}"

    def calculate_score(self):
        """
        Calculates the score for this tournament attempt based on correct, wrong answers,
        and the tournament's negative marking.
        """
        negative_marking_value = self.tournament.negative_marking
        self.score = (self.correct_answers * 1) - (self.wrong_answers * negative_marking_value)
        # Note: Skipped questions don't usually affect score unless specific rules
        self.save()

class TournamentLeaderboard(models.Model):
    """
    Aggregates user scores for a specific tournament, enabling rankings.
    This stores the overall best score for a user in a given tournament.
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="The authenticated user on the leaderboard (if applicable)."
    )
    guest_user = models.ForeignKey(
        UserOpenAccount, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="The guest user on the leaderboard (if applicable)."
    )
    tournament = models.ForeignKey(
        Tournament, 
        on_delete=models.CASCADE, 
        related_name='leaderboard_entries',
        help_text="The tournament for which this leaderboard entry exists."
    )
    
    # This stores the best (highest) single score achieved by the user in this specific tournament.
    total_score = models.FloatField(
        default=0, 
        help_text="The best (highest) score achieved by the user in this tournament across all valid attempts."
    ) 
    
    # Fields to help track daily high scorers for daily prize distribution
    last_daily_score = models.FloatField(
        default=0, 
        help_text="The highest score achieved by the user on the last day they participated."
    )
    last_daily_update = models.DateField(
        null=True, # Can be null if no daily score yet
        blank=True,
        help_text="The date of the last update to last_daily_score, useful for daily winner checks."
    )

    # Added: Last successful attempt date/time (for tie-breaking or display)
    last_attempt_datetime = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="The datetime of the attempt that resulted in the current 'total_score' or the latest completed attempt."
    )

    class Meta:
        verbose_name = "Tournament Leaderboard Entry"
        verbose_name_plural = "Tournament Leaderboard Entries"
        # Ensures that a unique combination of user (or guest) and tournament exists
        unique_together = ('user', 'guest_user', 'tournament') 
        # Ordering for overall leaderboard display (higher score, then faster time taken, then earlier attempt)
        ordering = ['-total_score', 'last_attempt_datetime'] 
        # Constraint to ensure either user or guest_user is set, but not both
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False, guest_user__isnull=True) |
                      models.Q(user__isnull=True, guest_user__isnull=False),
                name='either_user_or_guest_user_for_tournament_leaderboard'
            )
        ]

    def __str__(self):
        participant = "Unknown"
        if self.user:
            participant = self.user.email
        elif self.guest_user:
            participant = self.guest_user.id
        return f"{participant} - {self.tournament.title} - Top Score: {self.total_score}"