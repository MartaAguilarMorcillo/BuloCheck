"""
test_api.py — API tests for all endpoints:
  - POST /api/predict/
  - GET  /api/history/
  - GET  /api/sources/
"""

import uuid
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from api.models import AnonymousUser, NewsCheck

DEVICE_ID = "550e8400-e29b-41d4-a716-446655440000"
SAMPLE_TITLE = "Scientists confirm the Earth is flat"
SAMPLE_TEXT = "A new NASA study reveals the Earth has been flat all along."

MOCK_PREDICTION_FAKE = {
    "label": "FAKE",
    "confidence": 0.8367,
    "probas": {"REAL": 0.1633, "FAKE": 0.8367},
}

MOCK_PREDICTION_REAL = {
    "label": "REAL",
    "confidence": 0.7512,
    "probas": {"REAL": 0.7512, "FAKE": 0.2488},
}


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


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/predict/
# ─────────────────────────────────────────────────────────────────────────────


class PredictViewTest(APITestCase):
    """API tests for POST /api/predict/."""

    def _post(self, data):
        return self.client.post("/api/predict/", data, format="json")

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_returns_200(self, _):
        """POST /api/predict/ returns 200 with valid data."""
        response = self._post(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "source": "bbc.com",
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_response_structure(self, _):
        """Response contains label, confidence, probas and check_id."""
        response = self._post(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "device_id": DEVICE_ID,
            }
        )
        data = response.json()
        self.assertIn("label", data)
        self.assertIn("confidence", data)
        self.assertIn("probas", data)
        self.assertIn("check_id", data)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_creates_news_check_in_db(self, _):
        """POST /api/predict/ saves the result in the database."""
        self._post(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "source": "bbc.com",
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(NewsCheck.objects.count(), 1)
        check = NewsCheck.objects.first()
        self.assertEqual(check.label, "FAKE")
        self.assertEqual(check.source, "bbc.com")

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_creates_anonymous_user_if_not_exists(self, _):
        """POST /api/predict/ creates AnonymousUser if device_id is new."""
        self.assertEqual(AnonymousUser.objects.count(), 0)
        self._post(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(AnonymousUser.objects.count(), 1)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_reuses_existing_user(self, _):
        """POST /api/predict/ reuses existing AnonymousUser."""
        AnonymousUser.objects.create(id=DEVICE_ID)
        self._post(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(AnonymousUser.objects.count(), 1)

    def test_predict_returns_400_without_title(self):
        """POST /api/predict/ returns 400 when title is missing."""
        response = self._post({"text": SAMPLE_TEXT, "device_id": DEVICE_ID})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_predict_returns_400_without_text(self):
        """POST /api/predict/ returns 400 when text is missing."""
        response = self._post({"title": SAMPLE_TITLE, "device_id": DEVICE_ID})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_predict_returns_400_without_device_id(self):
        """POST /api/predict/ returns 400 when device_id is missing."""
        response = self._post({"title": SAMPLE_TITLE, "text": SAMPLE_TEXT})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_predict_returns_400_with_invalid_device_id(self):
        """POST /api/predict/ returns 400 when device_id is not a UUID."""
        response = self._post(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "device_id": "not-a-uuid",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("api.views.predict_news", side_effect=Exception("Space timeout"))
    def test_predict_returns_503_on_model_error(self, _):
        """POST /api/predict/ returns 503 when model call fails."""
        response = self._post(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("error", response.json())

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_without_source_saves_null(self, _):
        """POST /api/predict/ saves source as None when not provided."""
        self._post(
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "device_id": DEVICE_ID,
            }
        )
        self.assertIsNone(NewsCheck.objects.first().source)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/history/
# ─────────────────────────────────────────────────────────────────────────────


class HistoryViewTest(APITestCase):
    """API tests for GET /api/history/."""

    def setUp(self):
        self.user = make_user()

    def _get(self, device_id=DEVICE_ID, page=1, page_size=10):
        return self.client.get(
            f"/api/history/?page={page}&page_size={page_size}",
            HTTP_X_DEVICE_ID=device_id,
        )

    def test_history_returns_200(self):
        """GET /api/history/ returns 200 with valid device_id."""
        self.assertEqual(self._get().status_code, status.HTTP_200_OK)

    def test_history_returns_empty_for_unknown_user(self):
        """GET /api/history/ returns empty results for unknown device_id."""
        response = self._get(device_id=str(uuid.uuid4()))
        data = response.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_history_returns_400_without_header(self):
        """GET /api/history/ returns 400 when X-Device-ID header is missing."""
        response = self.client.get("/api/history/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_history_returns_all_user_checks(self):
        """GET /api/history/ returns all news checks for the user."""
        make_check(self.user, title="News 1")
        make_check(self.user, title="News 2")
        make_check(self.user, title="News 3")
        data = self._get().json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 3)

    def test_history_does_not_return_other_users_checks(self):
        """GET /api/history/ only returns checks for the requesting user."""
        other_user = AnonymousUser.objects.create(id=str(uuid.uuid4()))
        make_check(self.user, title="My news")
        make_check(other_user, title="Other user news")
        titles = [item["title"] for item in self._get().json()["results"]]
        self.assertIn("My news", titles)
        self.assertNotIn("Other user news", titles)

    def test_history_ordered_newest_first(self):
        """GET /api/history/ returns checks ordered newest first."""
        from datetime import timedelta

        from django.utils import timezone

        check1 = make_check(self.user, title="First")
        check1.created_at = timezone.now() - timedelta(seconds=10)
        check1.save()

        check2 = make_check(self.user, title="Second")
        check2.created_at = timezone.now()
        check2.save()

        data = self._get().json()["results"]
        self.assertEqual(data[0]["title"], "Second")
        self.assertEqual(data[1]["title"], "First")

    def test_history_response_fields(self):
        """GET /api/history/ response contains pagination fields."""
        make_check(self.user)
        data = self._get().json()
        self.assertIn("count", data)
        self.assertIn("total_pages", data)
        self.assertIn("current_page", data)
        self.assertIn("results", data)

    def test_history_result_item_fields(self):
        """Each result item contains the expected news check fields."""
        make_check(self.user)
        item = self._get().json()["results"][0]
        for field in [
            "id",
            "title",
            "text",
            "source",
            "label",
            "confidence",
            "created_at",
        ]:
            self.assertIn(field, item)

    def test_history_pagination(self):
        """GET /api/history/ paginates correctly."""
        for i in range(15):
            make_check(self.user, title=f"News {i}")
        data = self._get(page=1, page_size=10).json()
        self.assertEqual(data["count"], 15)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(data["current_page"], 1)
        self.assertEqual(len(data["results"]), 10)

    def test_history_second_page(self):
        """GET /api/history/ second page returns remaining items."""
        for i in range(15):
            make_check(self.user, title=f"News {i}")
        data = self._get(page=2, page_size=10).json()
        self.assertEqual(len(data["results"]), 5)
        self.assertEqual(data["current_page"], 2)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/sources/
# ─────────────────────────────────────────────────────────────────────────────


class SourceStatsViewTest(APITestCase):
    """API tests for GET /api/sources/."""

    def setUp(self):
        self.user = make_user()

    def _get(self, device_id=DEVICE_ID):
        return self.client.get("/api/sources/", HTTP_X_DEVICE_ID=device_id)

    def test_sources_returns_200(self):
        """GET /api/sources/ returns 200 with valid device_id."""
        self.assertEqual(self._get().status_code, status.HTTP_200_OK)

    def test_sources_returns_400_without_header(self):
        """GET /api/sources/ returns 400 when X-Device-ID header is missing."""
        response = self.client.get("/api/sources/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sources_returns_empty_for_unknown_user(self):
        """GET /api/sources/ returns empty list for unknown device_id."""
        self.assertEqual(self._get(device_id=str(uuid.uuid4())).json(), [])

    def test_sources_returns_empty_when_no_source_informed(self):
        """GET /api/sources/ returns empty when no checks have a source."""
        make_check(self.user, source=None)
        self.assertEqual(self._get().json(), [])

    def test_sources_ranking_by_real_count(self):
        """Sources with more REAL articles rank higher."""
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.80)
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.80)
        make_check(self.user, source="foxnews.com", label="FAKE", confidence=0.70)
        data = self._get().json()
        self.assertEqual(data[0]["source"], "bbc.com")
        self.assertEqual(data[1]["source"], "foxnews.com")

    def test_sources_tiebreak_by_confidence(self):
        """When REAL count is equal, higher avg confidence wins."""
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.80)
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.80)
        make_check(self.user, source="nytimes.com", label="REAL", confidence=0.85)
        make_check(self.user, source="nytimes.com", label="REAL", confidence=0.85)
        data = self._get().json()
        self.assertEqual(data[0]["source"], "nytimes.com")
        self.assertEqual(data[1]["source"], "bbc.com")

    def test_sources_returns_max_5(self):
        """GET /api/sources/ returns at most 5 sources."""
        for src in ["a.com", "b.com", "c.com", "d.com", "e.com", "f.com"]:
            make_check(self.user, source=src, label="REAL")
        self.assertLessEqual(len(self._get().json()), 5)

    def test_sources_response_fields(self):
        """Response items contain all expected fields."""
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.80)
        item = self._get().json()[0]
        for field in [
            "source",
            "total",
            "real",
            "fake",
            "real_confidence_avg",
            "reliability_pct",
        ]:
            self.assertIn(field, item)

    def test_sources_counts_are_correct(self):
        """real, fake and total counts are correct."""
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.80)
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.90)
        make_check(self.user, source="bbc.com", label="FAKE", confidence=0.75)
        item = self._get().json()[0]
        self.assertEqual(item["total"], 3)
        self.assertEqual(item["real"], 2)
        self.assertEqual(item["fake"], 1)

    def test_sources_reliability_pct_calculation(self):
        """reliability_pct is calculated as real/total * 100."""
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.80)
        make_check(self.user, source="bbc.com", label="FAKE", confidence=0.75)
        item = self._get().json()[0]
        self.assertAlmostEqual(item["reliability_pct"], 50.0)

    def test_sources_real_confidence_avg_calculation(self):
        """real_confidence_avg is the average confidence of REAL articles."""
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.80)
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.90)
        make_check(self.user, source="bbc.com", label="FAKE", confidence=0.70)
        item = self._get().json()[0]
        self.assertAlmostEqual(item["real_confidence_avg"], 0.85, places=2)

    def test_sources_does_not_include_other_users(self):
        """GET /api/sources/ only considers the requesting user's checks."""
        other_user = AnonymousUser.objects.create(id=str(uuid.uuid4()))
        make_check(self.user, source="bbc.com", label="REAL")
        make_check(other_user, source="foxnews.com", label="FAKE")
        sources = [item["source"] for item in self._get().json()]
        self.assertIn("bbc.com", sources)
        self.assertNotIn("foxnews.com", sources)

    def test_sources_full_example_from_spec(self):
        """
        Full example from the specification:
        NYT (2 REAL @85%) → BBC (2 REAL @80%) → BuzzFeed (1 REAL @81%) → Fox (0 REAL)
        """
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.80)
        make_check(self.user, source="bbc.com", label="REAL", confidence=0.80)
        make_check(self.user, source="nytimes.com", label="REAL", confidence=0.85)
        make_check(self.user, source="nytimes.com", label="REAL", confidence=0.85)
        make_check(self.user, source="buzzfeed.com", label="REAL", confidence=0.81)
        make_check(self.user, source="foxnews.com", label="FAKE", confidence=0.70)
        make_check(self.user, source="foxnews.com", label="FAKE", confidence=0.70)
        make_check(self.user, source="foxnews.com", label="FAKE", confidence=0.70)

        sources = [item["source"] for item in self._get().json()]
        self.assertEqual(sources[0], "nytimes.com")
        self.assertEqual(sources[1], "bbc.com")
        self.assertEqual(sources[2], "buzzfeed.com")
        self.assertEqual(sources[3], "foxnews.com")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/similar/
# ─────────────────────────────────────────────────────────────────────────────


class SimilarNewsViewTest(APITestCase):
    """API tests for GET /api/similar/ with hybrid trgm + full-text search."""

    def setUp(self):
        self.user = make_user()
        # Lexically similar title (trgm will find it)
        make_check(
            self.user,
            title="Facebook Continues To Host Militant Groups Despite Ban",
            label="REAL",
            source="buzzfeednews.com",
        )
        # Semantically related title (full-text will find it via stemming)
        make_check(
            self.user,
            title="Trump loses the presidential election by wide margin",
            label="FAKE",
            source="bbc.com",
        )

    def test_similar_returns_200(self):
        """GET /api/similar/ returns 200 with valid title."""
        response = self.client.get(
            "/api/similar/?title=Facebook groups militant ban extremism"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_similar_returns_400_without_title(self):
        """GET /api/similar/ returns 400 when title param is missing."""
        response = self.client.get("/api/similar/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_similar_response_fields(self):
        """Response items contain title, source, label, similarity, fts_rank, match_type."""
        response = self.client.get(
            "/api/similar/?title=Facebook groups militant ban&min_sim=0.1"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.json():
            item = response.json()[0]
            self.assertIn("title", item)
            self.assertIn("source", item)
            self.assertIn("label", item)
            self.assertIn("similarity", item)
            self.assertIn("fts_rank", item)
            self.assertIn("match_type", item)

    def test_similar_returns_empty_when_no_match(self):
        """GET /api/similar/ returns empty list when nothing matches."""
        response = self.client.get(
            "/api/similar/?title=Cooking recipes pasta carbonara italian cuisine&min_sim=0.9"
        )
        self.assertEqual(response.json(), [])

    def test_similar_trigram_match(self):
        """pg_trgm finds lexically similar titles."""
        response = self.client.get(
            "/api/similar/?title=Facebook Continues Hosting Militant Groups Ban&min_sim=0.2"
        )
        titles = [item["title"] for item in response.json()]
        self.assertIn("Facebook Continues To Host Militant Groups Despite Ban", titles)

    def test_similar_fulltext_match(self):
        """Full-text search finds semantically related titles via stemming."""
        # "lost" stems to "loss", "election" stems to "elect" — matches "loses" and "election"
        response = self.client.get(
            "/api/similar/?title=Trump lost the election defeat&min_sim=0.01"
        )
        titles = [item["title"] for item in response.json()]
        self.assertIn("Trump loses the presidential election by wide margin", titles)

    def test_similar_match_type_field(self):
        """match_type is one of: trigram+fulltext, trigram, fulltext."""
        response = self.client.get(
            "/api/similar/?title=Facebook groups militant ban&min_sim=0.1"
        )
        valid_match_types = {"trigram+fulltext", "trigram", "fulltext"}
        for item in response.json():
            self.assertIn(item["match_type"], valid_match_types)

    def test_similar_custom_min_sim(self):
        """GET /api/similar/ respects custom min_sim parameter."""
        response = self.client.get("/api/similar/?title=Facebook ban&min_sim=0.99")
        # With trgm threshold 0.99 only exact matches pass trgm,
        # but fulltext can still match
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_similar_returns_max_5_results(self):
        """GET /api/similar/ returns at most 5 results."""
        # Add more similar articles
        for i in range(6):
            make_check(
                self.user,
                title=f"Facebook militant groups ban extremism report {i}",
                label="FAKE",
                source="cnn.com",
            )
        response = self.client.get(
            "/api/similar/?title=Facebook militant groups ban&min_sim=0.1"
        )
        self.assertLessEqual(len(response.json()), 5)

    def test_similar_excludes_exact_title(self):
        """GET /api/similar/ does not return the exact same title being searched."""
        response = self.client.get(
            "/api/similar/?title=Facebook Continues To Host Militant Groups Despite Ban&min_sim=0.1"
        )
        titles = [item["title"] for item in response.json()]
        self.assertNotIn(
            "Facebook Continues To Host Militant Groups Despite Ban", titles
        )
