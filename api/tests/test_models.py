"""
test_models.py — Model tests for User and NewsCheck.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from api.models import NewsCheck

User = get_user_model()

SAMPLE_TITLE = "Scientists confirm the Earth is flat"
SAMPLE_TEXT = "A new NASA study reveals the Earth has been flat all along."


def make_user(email="test@example.com", password="testpass123"):
    return User.objects.create_user(email=email, password=password)


def make_check(user, label="REAL", confidence=0.75, news_source=None,
               title=SAMPLE_TITLE, text=SAMPLE_TEXT):
    check = NewsCheck.objects.create(
        title=title, text=text, news_source=news_source,
        label=label, confidence=confidence,
    )
    check.users.add(user)
    return check


# ─────────────────────────────────────────────────────────────────────────────
# User model
# ─────────────────────────────────────────────────────────────────────────────

class UserModelTest(TestCase):

    def test_create_user_with_email(self):
        """User is created with email as identifier."""
        user = make_user()
        self.assertEqual(user.email, "test@example.com")

    def test_password_is_hashed(self):
        """Password is stored hashed, never in plain text."""
        user = make_user()
        self.assertNotEqual(user.password, "testpass123")
        self.assertTrue(user.check_password("testpass123"))

    def test_user_is_active_by_default(self):
        """User is active by default."""
        user = make_user()
        self.assertTrue(user.is_active)

    def test_user_is_not_staff_by_default(self):
        """User is not staff by default."""
        user = make_user()
        self.assertFalse(user.is_staff)

    def test_user_created_at_is_set(self):
        """created_at is automatically set on creation."""
        user = make_user()
        self.assertIsNotNone(user.created_at)

    def test_str_representation(self):
        """__str__ returns the email."""
        user = make_user()
        self.assertEqual(str(user), "test@example.com")

    def test_duplicate_email_raises_error(self):
        """Creating two users with the same email raises IntegrityError."""
        make_user()
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="test@example.com", password="pass123")

    def test_db_table_name(self):
        """Model uses the correct DB table name."""
        self.assertEqual(User._meta.db_table, "users")

    def test_username_field_is_email(self):
        """USERNAME_FIELD is set to email."""
        self.assertEqual(User.USERNAME_FIELD, "email")


# ─────────────────────────────────────────────────────────────────────────────
# NewsCheck model
# ─────────────────────────────────────────────────────────────────────────────

class NewsCheckModelTest(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_create_news_check(self):
        check = make_check(self.user)
        self.assertEqual(check.label, "REAL")
        self.assertAlmostEqual(check.confidence, 0.75)

    def test_source_is_optional(self):
        check = NewsCheck.objects.create(
            title=SAMPLE_TITLE, text=SAMPLE_TEXT,
            label="FAKE", confidence=0.9,
        )
        check.users.add(self.user)
        self.assertIsNone(check.news_source)

    def test_label_real(self):
        check = make_check(self.user, label="REAL")
        self.assertEqual(check.label, "REAL")

    def test_label_fake(self):
        check = make_check(self.user, label="FAKE")
        self.assertEqual(check.label, "FAKE")

    def test_str_representation(self):
        check = make_check(self.user, label="FAKE", confidence=0.9)
        self.assertIn("FAKE", str(check))
        self.assertIn("90%", str(check))

    def test_ordering_by_created_at_desc(self):
        check1 = make_check(self.user, title="First news")
        check1.created_at = timezone.now() - timedelta(seconds=10)
        check1.save()

        check2 = make_check(self.user, title="Second news")
        check2.created_at = timezone.now()
        check2.save()

        checks = list(NewsCheck.objects.all())
        self.assertEqual(checks[0].title, "Second news")
        self.assertEqual(checks[1].title, "First news")

    def test_cascade_delete(self):
        """Deleting a user removes the relationship but not the NewsCheck."""
        make_check(self.user)
        make_check(self.user)
        self.assertEqual(NewsCheck.objects.count(), 2)
        self.user.delete()
        self.assertEqual(NewsCheck.objects.count(), 2)
        for check in NewsCheck.objects.all():
            self.assertEqual(check.users.count(), 0)

    def test_db_table_name(self):
        self.assertEqual(NewsCheck._meta.db_table, "news_checks")

    def test_user_relation(self):
        """NewsCheck is linked to the correct User."""
        check = make_check(self.user)
        self.assertIn(self.user, check.users.all())

    def test_related_name_checks(self):
        """User.checks returns all related NewsChecks."""
        make_check(self.user)
        make_check(self.user)
        self.assertEqual(self.user.checks.count(), 2)