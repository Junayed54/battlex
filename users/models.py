from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from django.contrib.auth.models import PermissionsMixin
from django.utils.timezone import now


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def is_guest(self):
        return False




class UserOpenAccount(models.Model):
    id = models.CharField(max_length=36, primary_key=True)  # UUID or unique string
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="open_accounts")

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    device = models.CharField(max_length=255, null=True, blank=True)
    browser = models.CharField(max_length=255, null=True, blank=True)
    os = models.CharField(max_length=255, null=True, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('limited', 'Limited'),
        ('blocked', 'Blocked'),
        ('deleted', 'Deleted'),
        ('removed', 'Removed'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    class Meta:
        db_table = "tbl_user_open_account"

    def __str__(self):
        return f"{self.id} - {self.status}"
    # In UserOpenAccount
    @property
    def is_guest(self):
        return True
    @property
    def is_authenticated(self):
        return False




class UserActivityLog(models.Model):
    user = models.ForeignKey(UserOpenAccount, on_delete=models.CASCADE, related_name="activities")
    url = models.CharField(max_length=2048)  # Store the visited URL
    timestamp = models.DateTimeField(default=now)  # Store time of visit

    class Meta:
        db_table = "tbl_user_activity"

    def __str__(self):
        return f"{self.user.id} visited {self.url} at {self.timestamp}"