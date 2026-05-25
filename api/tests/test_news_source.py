"""
test_news_source.py — Tests for NewsSource model, source_utils and SourceLookupView.

Covers:
  - NewsSource model constraints (unique name, unique domain)
  - get_or_create_source(): known domain, unknown domain with Clearbit,
    Clearbit failure fallback
  - GET /api/sources/lookup/ endpoint
  - POST /api/predict/ with domain: source resolved and returned
  - GET /api/sources/ returns NewsSource objects with logo
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import AnonymousUser, NewsCheck, NewsSource
from api.source_utils import get_or_create_source

DEVICE_ID = "550e8400-e29b-41d4-a716-446655440000"
SAMPLE_TITLE = "Scientists discover new evidence of climate change in the Arctic"
SAMPLE_TEXT = (
    "A team of researchers at Oxford University has announced a major breakthrough "
    "in climate science that could reshape our understanding of polar ice dynamics. "
    "The findings, published in Nature, show accelerating ice loss over the past decade."
)

MOCK_PREDICTION = {
    "label": "REAL",
    "confidence": 0.87,
    "probas": {"REAL": 0.87, "FAKE": 0.13},
}


# ═══════════════════════════════════════════════════════════════════════════
# 1. NewsSource model tests
# ═══════════════════════════════════════════════════════════════════════════


class NewsSourceModelTest(TestCase):

    def test_create_predefined_source(self):
        """NewsSource is created with all fields."""
        source = NewsSource.objects.get(domain="bbc.com")
        self.assertEqual(source.name, "BBC")
        self.assertTrue(source.is_predefined)
        self.assertIsNotNone(source.logo_url)

    def test_logo_url_is_optional(self):
        """NewsSource can be created without a logo URL."""
        source = NewsSource.objects.create(
            name="Unknown Source", domain="unknown-test.com"
        )
        self.assertIsNone(source.logo_url)

    def test_domain_is_unique(self):
        """Two sources cannot share the same domain."""
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            NewsSource.objects.create(name="BBC Copy", domain="bbc.com")

    def test_name_is_unique(self):
        """Two sources cannot share the same name."""
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            NewsSource.objects.create(name="BBC", domain="bbc-copy.com")

    def test_str_representation(self):
        """__str__ returns name and domain."""
        source = NewsSource.objects.get(domain="bbc.com")
        self.assertIn("BBC", str(source))
        self.assertIn("bbc.com", str(source))

    def test_is_predefined_defaults_to_false(self):
        """is_predefined defaults to False for new sources."""
        source = NewsSource.objects.create(
            name="New Source Test", domain="newsourcetest.com"
        )
        self.assertFalse(source.is_predefined)

    def test_predefined_sources_loaded_by_migration(self):
        """Migration loads 47 predefined sources."""
        count = NewsSource.objects.filter(is_predefined=True).count()
        self.assertEqual(count, 47)

    def test_bbc_predefined_source_exists(self):
        """BBC is in the predefined sources."""
        source = NewsSource.objects.get(domain="bbc.com")
        self.assertEqual(source.name, "BBC")
        self.assertTrue(source.is_predefined)
        self.assertIsNotNone(source.logo_url)

    def test_corrected_domains_exist(self):
        """Corrected domains are stored correctly."""
        self.assertTrue(NewsSource.objects.filter(domain="thetimes.com").exists())
        self.assertTrue(NewsSource.objects.filter(domain="dailymail.com").exists())
        self.assertTrue(NewsSource.objects.filter(domain="abcnews.com").exists())


# ═══════════════════════════════════════════════════════════════════════════
# 2. source_utils tests
# ═══════════════════════════════════════════════════════════════════════════


class GetOrCreateSourceTest(TestCase):

    def test_returns_existing_predefined_source(self):
        source = get_or_create_source("bbc.com")
        self.assertEqual(source.name, "BBC")
        self.assertTrue(source.is_predefined)

    def test_new_source_name_is_none(self):
        """New source name is None — frontend shows domain instead."""
        source = get_or_create_source("unknownnewssite.com")
        self.assertIsNone(source.name)

    def test_domain_lookup_is_case_insensitive(self):
        source = get_or_create_source("BBC.com")
        self.assertEqual(source.domain, "bbc.com")

    def test_new_source_has_favicon_logo(self):
        """New source gets a Google Favicon URL as logo."""
        source = get_or_create_source("unknownnewssite.com")
        self.assertIsNotNone(source.logo_url)
        self.assertIn("google.com/s2/favicons", source.logo_url)

    def test_hyphenated_domain_has_favicon_logo(self):
        """New source from hyphenated domain gets favicon logo."""
        source = get_or_create_source("fox-news-test.com")
        self.assertIsNone(source.name)
        self.assertIn("fox-news-test.com", source.logo_url)

    def test_does_not_duplicate_on_repeated_calls(self):
        """get_or_create_source does not create duplicates."""
        source1 = get_or_create_source("testnews.com")
        source2 = get_or_create_source("testnews.com")
        self.assertEqual(source1.id, source2.id)
        self.assertEqual(NewsSource.objects.filter(domain="testnews.com").count(), 1)


# ═══════════════════════════════════════════════════════════════════════════
# 3. SourceLookupView tests — GET /api/sources/lookup/
# ═══════════════════════════════════════════════════════════════════════════


class SourceLookupViewTest(APITestCase):

    def test_lookup_known_domain_returns_source(self):
        """GET /api/sources/lookup/?domain=bbc.com returns BBC source."""
        response = self.client.get("/api/sources/lookup/?domain=bbc.com")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["name"], "BBC")
        self.assertEqual(data["domain"], "bbc.com")
        self.assertIsNotNone(data["logo_url"])
        self.assertTrue(data["is_predefined"])

    def test_lookup_unknown_domain_returns_404(self):
        """GET /api/sources/lookup/?domain=unknown.com returns 404."""
        response = self.client.get("/api/sources/lookup/?domain=unknownsite12345.com")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_lookup_without_domain_returns_400(self):
        """GET /api/sources/lookup/ without domain param returns 400."""
        response = self.client.get("/api/sources/lookup/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lookup_response_fields(self):
        """Lookup response contains all expected fields."""
        response = self.client.get("/api/sources/lookup/?domain=bbc.com")
        data = response.json()
        for field in ["id", "name", "domain", "logo_url", "is_predefined"]:
            self.assertIn(field, data)


# ═══════════════════════════════════════════════════════════════════════════
# 4. PredictView with domain — source resolved and returned
# ═══════════════════════════════════════════════════════════════════════════


class PredictWithSourceTest(APITestCase):

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION)
    def test_predict_with_known_domain_returns_source(self, _):
        """POST /api/predict/ with known domain returns full source object."""
        response = self.client.post(
            "/api/predict/",
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "domain": "bbc.com",
                "device_id": DEVICE_ID,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("news_source", data)
        self.assertEqual(data["news_source"]["name"], "BBC")
        self.assertEqual(data["news_source"]["domain"], "bbc.com")
        self.assertIsNotNone(data["news_source"]["logo_url"])

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION)
    def test_predict_without_domain_returns_null_source(self, _):
        """POST /api/predict/ without domain returns null news_source."""
        response = self.client.post(
            "/api/predict/",
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "device_id": DEVICE_ID,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.json()["news_source"])

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION)
    @patch("api.views.get_or_create_source")
    def test_predict_with_unknown_domain_creates_source(self, mock_get_source, _):
        """POST /api/predict/ with unknown domain calls get_or_create_source."""
        new_source = NewsSource.objects.create(
            name="Unknown News",
            domain="unknownnews.com",
            is_predefined=False,
        )
        mock_get_source.return_value = new_source

        response = self.client.post(
            "/api/predict/",
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "domain": "unknownnews.com",
                "device_id": DEVICE_ID,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_get_source.assert_called_once_with("unknownnews.com")

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION)
    def test_predict_saves_news_source_fk_in_db(self, _):
        """POST /api/predict/ saves the news_source FK in the NewsCheck record."""
        self.client.post(
            "/api/predict/",
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "domain": "bbc.com",
                "device_id": DEVICE_ID,
            },
            format="json",
        )

        check = NewsCheck.objects.first()
        self.assertIsNotNone(check.news_source)
        self.assertEqual(check.news_source.name, "BBC")


# ═══════════════════════════════════════════════════════════════════════════
# 5. SourceStatsView with NewsSource objects
# ═══════════════════════════════════════════════════════════════════════════


class SourceStatsWithNewsSourceTest(APITestCase):

    def setUp(self):
        self.user = AnonymousUser.objects.create(id=DEVICE_ID)
        self.bbc = NewsSource.objects.get(domain="bbc.com")
        self.nyt = NewsSource.objects.get(domain="nytimes.com")

    def _make_check(self, source, label, confidence=0.80):
        check = NewsCheck.objects.create(
            title=SAMPLE_TITLE,
            text=SAMPLE_TEXT,
            news_source=source,
            label=label,
            confidence=confidence,
        )
        check.users.add(self.user)
        return check

    def test_sources_response_includes_news_source_object(self):
        """GET /api/sources/ returns full news_source object for each entry."""
        self._make_check(self.bbc, "REAL")
        response = self.client.get("/api/sources/", HTTP_X_DEVICE_ID=DEVICE_ID)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.json()[0]
        self.assertIn("news_source", item)
        self.assertIn("name", item["news_source"])
        self.assertIn("logo_url", item["news_source"])
        self.assertIn("domain", item["news_source"])

    def test_sources_ranking_uses_news_source(self):
        """GET /api/sources/ ranks sources correctly using news_source FK."""
        self._make_check(self.bbc, "REAL", confidence=0.80)
        self._make_check(self.bbc, "REAL", confidence=0.80)
        self._make_check(self.nyt, "REAL", confidence=0.85)
        self._make_check(self.nyt, "REAL", confidence=0.85)

        response = self.client.get("/api/sources/", HTTP_X_DEVICE_ID=DEVICE_ID)
        data = response.json()
        # NYT has higher avg confidence → ranks first despite same REAL count
        self.assertEqual(data[0]["news_source"]["name"], "The New York Times")
        self.assertEqual(data[1]["news_source"]["name"], "BBC")

    def test_sources_logo_url_present_for_predefined(self):
        """Predefined sources include logo_url in the response."""
        self._make_check(self.bbc, "REAL")
        response = self.client.get("/api/sources/", HTTP_X_DEVICE_ID=DEVICE_ID)
        item = response.json()[0]
        self.assertIsNotNone(item["news_source"]["logo_url"])
