"""
test_serializers.py — Tests for PredictRequestSerializer and NewsCheckSerializer.
"""

from django.test import TestCase

from api.models import AnonymousUser, NewsCheck, NewsSource
from api.serializers import NewsCheckSerializer, PredictRequestSerializer

DEVICE_ID = "550e8400-e29b-41d4-a716-446655440000"
SAMPLE_TITLE = "Scientists confirm the Earth is flat"
SAMPLE_TEXT = "A new NASA study reveals the Earth has been flat all along."


class PredictRequestSerializerTest(TestCase):
    """Tests for PredictRequestSerializer."""

    def _get_serializer(self, data):
        return PredictRequestSerializer(data=data)

    def test_valid_data_with_source(self):
        """Serializer is valid with all fields including source."""
        s = self._get_serializer(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "source": "bbc.com",
                "device_id": DEVICE_ID,
            }
        )
        self.assertTrue(s.is_valid())

    def test_valid_data_without_source(self):
        """Serializer is valid without optional source field."""
        s = self._get_serializer(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "device_id": DEVICE_ID,
            }
        )
        self.assertTrue(s.is_valid())

    def test_missing_title_is_invalid(self):
        """Serializer is invalid when title is missing."""
        s = self._get_serializer(
            {
                "text": SAMPLE_TEXT,
                "device_id": DEVICE_ID,
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("title", s.errors)

    def test_missing_text_is_invalid(self):
        """Serializer is invalid when text is missing."""
        s = self._get_serializer(
            {
                "title": SAMPLE_TITLE,
                "device_id": DEVICE_ID,
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("text", s.errors)

    def test_missing_device_id_is_invalid(self):
        """Serializer is invalid when device_id is missing."""
        s = self._get_serializer(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("device_id", s.errors)

    def test_invalid_device_id_format(self):
        """Serializer is invalid when device_id is not a valid UUID."""
        s = self._get_serializer(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "device_id": "not-a-uuid",
            }
        )
        self.assertFalse(s.is_valid())
        self.assertIn("device_id", s.errors)

    def test_blank_source_is_allowed(self):
        """Serializer accepts blank source."""
        s = self._get_serializer(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "source": "",
                "device_id": DEVICE_ID,
            }
        )
        self.assertTrue(s.is_valid())


class NewsCheckSerializerTest(TestCase):
    """Tests for NewsCheckSerializer."""

    def setUp(self):
        self.user = AnonymousUser.objects.create(id=DEVICE_ID)
        self.bbc = NewsSource.objects.get(domain="bbc.com")
        self.check = NewsCheck.objects.create(
            user=self.user,
            title=SAMPLE_TITLE,
            text=SAMPLE_TEXT,
            news_source=self.bbc,
            label="REAL",
            confidence=0.75,
        )

    def test_serializes_correct_fields(self):
        s = NewsCheckSerializer(self.check)
        data = s.data
        for field in ["id", "title", "text", "news_source", "label", "confidence", "created_at"]:
            self.assertIn(field, data)

    def test_does_not_expose_user_id(self):
        """Serializer does not expose user or user_id."""
        s = NewsCheckSerializer(self.check)
        self.assertNotIn("user", s.data)
        self.assertNotIn("user_id", s.data)

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
