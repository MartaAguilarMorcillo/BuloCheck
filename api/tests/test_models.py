"""
test_models.py — Model tests for AnonymousUser and NewsCheck.
"""

from django.db import IntegrityError
from django.test import TestCase

from api.models import AnonymousUser, NewsCheck

DEVICE_ID = "550e8400-e29b-41d4-a716-446655440000"
SAMPLE_TITLE = "Scientists confirm the Earth is flat"
SAMPLE_TEXT = "A new NASA study reveals the Earth has been flat all along."


def make_user(device_id=DEVICE_ID):
    return AnonymousUser.objects.create(id=device_id)


def make_check(
    user,
    label="REAL",
    confidence=0.75,
    source="bbc.com",
    title=SAMPLE_TITLE,
    text=SAMPLE_TEXT,
):
    return NewsCheck.objects.create(
        user=user,
        title=title,
        text=text,
        source=source,
        label=label,
        confidence=confidence,
    )


class AnonymousUserModelTest(TestCase):
    """Tests for the AnonymousUser model."""

    def test_create_user_with_uuid(self):
        """AnonymousUser is created with a valid UUID."""
        user = make_user()
        self.assertEqual(str(user.id), DEVICE_ID)

    def test_user_created_at_is_set(self):
        """created_at is automatically set on creation."""
        user = make_user()
        self.assertIsNotNone(user.created_at)

    def test_str_representation(self):
        """__str__ returns the UUID as string."""
        user = make_user()
        self.assertEqual(str(user), DEVICE_ID)

    def test_user_uuid_is_primary_key(self):
        """UUID is the primary key."""
        user = make_user()
        self.assertEqual(str(user.pk), DEVICE_ID)

    def test_duplicate_device_id_raises_error(self):
        """Creating two users with the same device_id raises IntegrityError."""
        make_user()
        with self.assertRaises(IntegrityError):
            AnonymousUser.objects.create(id=DEVICE_ID)

    def test_db_table_name(self):
        """Model uses the correct DB table name."""
        self.assertEqual(AnonymousUser._meta.db_table, "anonymous_users")


class NewsCheckModelTest(TestCase):
    """Tests for the NewsCheck model."""

    def setUp(self):
        self.user = make_user()

    def test_create_news_check(self):
        """NewsCheck is created with all fields."""
        check = make_check(self.user)
        self.assertEqual(check.label, "REAL")
        self.assertEqual(check.source, "bbc.com")
        self.assertAlmostEqual(check.confidence, 0.75)

    def test_source_is_optional(self):
        """NewsCheck can be created without a source."""
        check = NewsCheck.objects.create(
            user=self.user,
            title=SAMPLE_TITLE,
            text=SAMPLE_TEXT,
            label="FAKE",
            confidence=0.9,
        )
        self.assertIsNone(check.source)

    def test_label_real(self):
        """Label can be set to REAL."""
        check = make_check(self.user, label="REAL")
        self.assertEqual(check.label, "REAL")

    def test_label_fake(self):
        """Label can be set to FAKE."""
        check = make_check(self.user, label="FAKE")
        self.assertEqual(check.label, "FAKE")

    def test_str_representation(self):
        """__str__ returns label, confidence and truncated title."""
        check = make_check(self.user, label="FAKE", confidence=0.9)
        self.assertIn("FAKE", str(check))
        self.assertIn("90%", str(check))

    def test_ordering_by_created_at_desc(self):
        """NewsChecks are ordered by created_at descending."""
        make_check(self.user, title="First news")
        make_check(self.user, title="Second news")
        checks = list(NewsCheck.objects.all())
        self.assertEqual(checks[0].title, "Second news")
        self.assertEqual(checks[1].title, "First news")

    def test_cascade_delete(self):
        """Deleting a user deletes all their NewsChecks."""
        make_check(self.user)
        make_check(self.user)
        self.assertEqual(NewsCheck.objects.count(), 2)
        self.user.delete()
        self.assertEqual(NewsCheck.objects.count(), 0)

    def test_db_table_name(self):
        """Model uses the correct DB table name."""
        self.assertEqual(NewsCheck._meta.db_table, "news_checks")

    def test_user_relation(self):
        """NewsCheck is linked to the correct AnonymousUser."""
        check = make_check(self.user)
        self.assertEqual(check.user, self.user)

    def test_related_name_checks(self):
        """AnonymousUser.checks returns all related NewsChecks."""
        make_check(self.user)
        make_check(self.user)
        self.assertEqual(self.user.checks.count(), 2)
