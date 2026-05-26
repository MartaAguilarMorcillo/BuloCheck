"""
test_serializers.py — Tests for PredictRequestSerializer and NewsCheckSerializer.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from api.models import NewsCheck, NewsSource
from api.serializers import NewsCheckSerializer, PredictRequestSerializer

User = get_user_model()

SAMPLE_TITLE = "Scientists confirm the Earth is flat"
SAMPLE_TEXT = "A new NASA study reveals the Earth has been flat all along."


class PredictRequestSerializerTest(TestCase):
    """Tests for PredictRequestSerializer."""

    def _get_serializer(self, data):
        return PredictRequestSerializer(data=data)

    def test_valid_data_with_domain(self):
        """Serializer is valid with all fields including domain."""
        s = self._get_serializer({
            "title": SAMPLE_TITLE,
            "text": SAMPLE_TEXT,
            "domain": "bbc.com",
        })
        self.assertTrue(s.is_valid())

    def test_valid_data_without_domain(self):
        """Serializer is valid without optional domain field."""
        s = self._get_serializer({
            "title": SAMPLE_TITLE,
            "text": SAMPLE_TEXT,
        })
        self.assertTrue(s.is_valid())

    def test_missing_title_is_invalid(self):
        """Serializer is invalid when title is missing."""
        s = self._get_serializer({"text": SAMPLE_TEXT})
        self.assertFalse(s.is_valid())
        self.assertIn("title", s.errors)

    def test_missing_text_is_invalid(self):
        """Serializer is invalid when text is missing."""
        s = self._get_serializer({"title": SAMPLE_TITLE})
        self.assertFalse(s.is_valid())
        self.assertIn("text", s.errors)

    def test_blank_domain_is_allowed(self):
        """Serializer accepts blank domain."""
        s = self._get_serializer({
            "title": SAMPLE_TITLE,
            "text": SAMPLE_TEXT,
            "domain": "",
        })
        self.assertTrue(s.is_valid())


class NewsCheckSerializerTest(TestCase):
    """Tests for NewsCheckSerializer."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.bbc = NewsSource.objects.get(domain="bbc.com")
        self.check = NewsCheck.objects.create(
            title=SAMPLE_TITLE,
            text=SAMPLE_TEXT,
            news_source=self.bbc,
            label="REAL",
            confidence=0.75,
        )
        self.check.users.add(self.user)

    def test_serializes_correct_fields(self):
        s = NewsCheckSerializer(self.check)
        for field in ["id", "title", "text", "news_source",
                      "label", "confidence", "created_at"]:
            self.assertIn(field, s.data)

    def test_does_not_expose_user(self):
        """Serializer does not expose user or user_id."""
        s = NewsCheckSerializer(self.check)
        self.assertNotIn("user", s.data)
        self.assertNotIn("user_id", s.data)
        self.assertNotIn("users", s.data)

    def test_label_value(self):
        """Serializer returns correct label value."""
        s = NewsCheckSerializer(self.check)
        self.assertEqual(s.data["label"], "REAL")

    def test_confidence_value(self):
        """Serializer returns correct confidence value."""
        s = NewsCheckSerializer(self.check)
        self.assertAlmostEqual(float(s.data["confidence"]), 0.75)

    def test_source_value(self):
        """Serializer returns correct news_source object."""
        s = NewsCheckSerializer(self.check)
        self.assertEqual(s.data["news_source"]["domain"], "bbc.com")
        self.assertEqual(s.data["news_source"]["name"], "BBC")