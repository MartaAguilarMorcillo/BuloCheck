import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model using email as the unique identifier.
    No username — email + password only.
    """
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email


class NewsSource(models.Model):
    """Represents a news outlet."""
    name = models.CharField(max_length=200, unique=True, null=True, blank=True)
    domain = models.CharField(max_length=200, unique=True)
    logo_url = models.URLField(max_length=500, null=True, blank=True)
    is_predefined = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "news_sources"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.domain})"


class NewsCheck(models.Model):
    """Stores each news article analyzed, shared across users."""

    LABEL_CHOICES = [
        ("REAL", "Real"),
        ("FAKE", "Fake"),
    ]

    # Many-to-many: one article can be analyzed by multiple users
    users = models.ManyToManyField(
        User,
        related_name="checks",
        db_table="news_check_users",
    )
    title = models.TextField()
    text = models.TextField()
    news_source = models.ForeignKey(
        NewsSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checks",
    )
    label = models.CharField(max_length=4, choices=LABEL_CHOICES)
    confidence = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "news_checks"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label} ({self.confidence:.0%}) — {self.title[:60]}"