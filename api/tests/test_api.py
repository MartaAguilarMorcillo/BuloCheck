"""
test_api.py — API tests for all endpoints:
  - POST /api/predict/
  - GET  /api/history/
  - GET  /api/sources/
  - GET  /api/similar/
"""

import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import NewsCheck, NewsSource

User = get_user_model()

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


def make_user(email="test@example.com", password="testpass123"):
    return User.objects.create_user(email=email, password=password)


def make_check(
    user,
    label="REAL",
    confidence=0.75,
    news_source=None,
    title=SAMPLE_TITLE,
    text=SAMPLE_TEXT,
):
    check = NewsCheck.objects.create(
        title=title,
        text=text,
        news_source=news_source,
        label=label,
        confidence=confidence,
    )
    check.users.add(user)
    return check


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/predict/
# ─────────────────────────────────────────────────────────────────────────────


class PredictViewTest(APITestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    def _post(self, data):
        return self.client.post("/api/predict/", data, format="json")

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_returns_200(self, _):
        response = self._post({"title": SAMPLE_TITLE, "text": SAMPLE_TEXT})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_response_structure(self, _):
        response = self._post({"title": SAMPLE_TITLE, "text": SAMPLE_TEXT})
        data = response.json()
        self.assertIn("label", data)
        self.assertIn("confidence", data)
        self.assertIn("probas", data)
        self.assertIn("check_id", data)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_creates_news_check_in_db(self, _):
        self._post({"title": SAMPLE_TITLE, "text": SAMPLE_TEXT, "domain": "bbc.com"})
        self.assertEqual(NewsCheck.objects.count(), 1)
        check = NewsCheck.objects.first()
        self.assertEqual(check.label, "FAKE")
        self.assertEqual(check.news_source.domain, "bbc.com")

    def test_predict_returns_401_without_auth(self):
        """POST /api/predict/ returns 401 when not authenticated."""
        self.client.force_authenticate(user=None)
        response = self._post({"title": SAMPLE_TITLE, "text": SAMPLE_TEXT})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_predict_returns_400_without_title(self):
        response = self._post({"text": SAMPLE_TEXT})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_predict_returns_400_without_text(self):
        response = self._post({"title": SAMPLE_TITLE})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("api.views.predict_news", side_effect=Exception("Space timeout"))
    def test_predict_returns_503_on_model_error(self, _):
        response = self._post({"title": SAMPLE_TITLE, "text": SAMPLE_TEXT})
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("error", response.json())

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_without_domain_saves_null_source(self, _):
        self._post({"title": SAMPLE_TITLE, "text": SAMPLE_TEXT})
        self.assertIsNone(NewsCheck.objects.first().news_source)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_links_check_to_authenticated_user(self, _):
        self._post({"title": SAMPLE_TITLE, "text": SAMPLE_TEXT})
        check = NewsCheck.objects.first()
        self.assertIn(self.user, check.users.all())


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/history/
# ─────────────────────────────────────────────────────────────────────────────


class HistoryViewTest(APITestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    def _get(self, page=1, page_size=10):
        return self.client.get(f"/api/history/?page={page}&page_size={page_size}")

    def test_history_returns_200(self):
        self.assertEqual(self._get().status_code, status.HTTP_200_OK)

    def test_history_returns_401_without_auth(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(
            self.client.get("/api/history/").status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_history_returns_empty_when_no_checks(self):
        data = self._get().json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_history_returns_all_user_checks(self):
        make_check(self.user, title="News 1")
        make_check(self.user, title="News 2")
        make_check(self.user, title="News 3")
        data = self._get().json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 3)

    def test_history_does_not_return_other_users_checks(self):
        other_user = make_user(email="other@example.com")
        make_check(self.user, title="My news")
        make_check(other_user, title="Other user news")
        titles = [item["title"] for item in self._get().json()["results"]]
        self.assertIn("My news", titles)
        self.assertNotIn("Other user news", titles)

    def test_history_ordered_newest_first(self):
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
        make_check(self.user)
        data = self._get().json()
        for field in ["count", "total_pages", "current_page", "results"]:
            self.assertIn(field, data)

    def test_history_result_item_fields(self):
        make_check(self.user)
        item = self._get().json()["results"][0]
        for field in [
            "id",
            "title",
            "text",
            "news_source",
            "label",
            "confidence",
            "created_at",
        ]:
            self.assertIn(field, item)

    def test_history_pagination(self):
        for i in range(15):
            make_check(self.user, title=f"News {i}")
        data = self._get(page=1, page_size=10).json()
        self.assertEqual(data["count"], 15)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(len(data["results"]), 10)

    def test_history_second_page(self):
        for i in range(15):
            make_check(self.user, title=f"News {i}")
        data = self._get(page=2, page_size=10).json()
        self.assertEqual(len(data["results"]), 5)
        self.assertEqual(data["current_page"], 2)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/sources/
# ─────────────────────────────────────────────────────────────────────────────


class SourceStatsViewTest(APITestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.bbc = NewsSource.objects.get(domain="bbc.com")
        self.nyt = NewsSource.objects.get(domain="nytimes.com")
        self.fox = NewsSource.objects.get(domain="foxnews.com")
        self.buzzfeed = NewsSource.objects.get(domain="buzzfeednews.com")

    def _get(self):
        return self.client.get("/api/sources/")

    def test_sources_returns_401_without_auth(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(
            self.client.get("/api/sources/").status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_sources_returns_empty_when_no_source_informed(self):
        make_check(self.user, news_source=None)
        self.assertEqual(self._get().json(), [])

    def test_sources_ranking_by_real_count(self):
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.80)
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.80)
        make_check(self.user, news_source=self.fox, label="FAKE", confidence=0.70)
        data = self._get().json()
        self.assertEqual(data[0]["news_source"]["domain"], "bbc.com")
        self.assertEqual(data[1]["news_source"]["domain"], "foxnews.com")

    def test_sources_tiebreak_by_confidence(self):
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.80)
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.80)
        make_check(self.user, news_source=self.nyt, label="REAL", confidence=0.85)
        make_check(self.user, news_source=self.nyt, label="REAL", confidence=0.85)
        data = self._get().json()
        self.assertEqual(data[0]["news_source"]["domain"], "nytimes.com")
        self.assertEqual(data[1]["news_source"]["domain"], "bbc.com")

    def test_sources_returns_max_5(self):
        for domain in [
            "bbc.com",
            "nytimes.com",
            "foxnews.com",
            "cnn.com",
            "theguardian.com",
            "reuters.com",
        ]:
            src = NewsSource.objects.get(domain=domain)
            make_check(self.user, news_source=src, label="REAL")
        self.assertLessEqual(len(self._get().json()), 5)

    def test_sources_response_fields(self):
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.80)
        item = self._get().json()[0]
        for field in [
            "news_source",
            "total",
            "real",
            "fake",
            "real_confidence_avg",
            "reliability_pct",
        ]:
            self.assertIn(field, item)
        for field in ["id", "name", "domain", "logo_url", "is_predefined"]:
            self.assertIn(field, item["news_source"])

    def test_sources_counts_are_correct(self):
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.80)
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.90)
        make_check(self.user, news_source=self.bbc, label="FAKE", confidence=0.75)
        item = self._get().json()[0]
        self.assertEqual(item["total"], 3)
        self.assertEqual(item["real"], 2)
        self.assertEqual(item["fake"], 1)

    def test_sources_reliability_pct_calculation(self):
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.80)
        make_check(self.user, news_source=self.bbc, label="FAKE", confidence=0.75)
        item = self._get().json()[0]
        self.assertAlmostEqual(item["reliability_pct"], 50.0)

    def test_sources_real_confidence_avg_calculation(self):
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.80)
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.90)
        make_check(self.user, news_source=self.bbc, label="FAKE", confidence=0.70)
        item = self._get().json()[0]
        self.assertAlmostEqual(item["real_confidence_avg"], 0.85, places=2)

    def test_sources_does_not_include_other_users(self):
        other_user = make_user(email="other@example.com")
        make_check(self.user, news_source=self.bbc, label="REAL")
        make_check(other_user, news_source=self.fox, label="FAKE")
        domains = [item["news_source"]["domain"] for item in self._get().json()]
        self.assertIn("bbc.com", domains)
        self.assertNotIn("foxnews.com", domains)

    def test_sources_full_example_from_spec(self):
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.80)
        make_check(self.user, news_source=self.bbc, label="REAL", confidence=0.80)
        make_check(self.user, news_source=self.nyt, label="REAL", confidence=0.85)
        make_check(self.user, news_source=self.nyt, label="REAL", confidence=0.85)
        make_check(self.user, news_source=self.buzzfeed, label="REAL", confidence=0.81)
        make_check(self.user, news_source=self.fox, label="FAKE", confidence=0.70)
        make_check(self.user, news_source=self.fox, label="FAKE", confidence=0.70)
        make_check(self.user, news_source=self.fox, label="FAKE", confidence=0.70)

        domains = [item["news_source"]["domain"] for item in self._get().json()]
        self.assertEqual(domains[0], "nytimes.com")
        self.assertEqual(domains[1], "bbc.com")
        self.assertEqual(domains[2], "buzzfeednews.com")
        self.assertEqual(domains[3], "foxnews.com")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/similar/
# ─────────────────────────────────────────────────────────────────────────────


class SimilarNewsViewTest(APITestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.bbc = NewsSource.objects.get(domain="bbc.com")
        self.buzzfeed = NewsSource.objects.get(domain="buzzfeednews.com")

        make_check(
            self.user,
            title="Facebook Continues To Host Militant Groups And Ads Despite Ban",
            label="REAL",
            news_source=self.buzzfeed,
        )
        make_check(
            self.user,
            title="Trump loses the presidential election by wide margin",
            label="FAKE",
            news_source=self.bbc,
        )

    def test_similar_returns_200(self):
        response = self.client.get("/api/similar/?title=Facebook groups militant ban")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_similar_returns_401_without_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/similar/?title=Facebook")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_similar_returns_400_without_title(self):
        response = self.client.get("/api/similar/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_similar_response_fields(self):
        response = self.client.get(
            "/api/similar/?title=Facebook groups militant ban&min_sim=0.1"
        )
        if response.json():
            item = response.json()[0]
            for field in [
                "title",
                "source_name",
                "source_logo",
                "label",
                "similarity",
                "fts_rank",
                "match_type",
            ]:
                self.assertIn(field, item)

    def test_similar_returns_empty_when_no_match(self):
        response = self.client.get(
            "/api/similar/?title=Cooking recipes pasta carbonara&min_sim=0.9"
        )
        self.assertEqual(response.json(), [])

    def test_similar_trigram_match(self):
        response = self.client.get(
            "/api/similar/?title=Facebook Continues Hosting Militant Groups Ban&min_sim=0.2"
        )
        titles = [item["title"] for item in response.json()]
        self.assertIn(
            "Facebook Continues To Host Militant Groups And Ads Despite Ban", titles
        )

    def test_similar_fulltext_match(self):
        response = self.client.get(
            "/api/similar/?title=Trump lost the election defeat&min_sim=0.01"
        )
        titles = [item["title"] for item in response.json()]
        self.assertIn("Trump loses the presidential election by wide margin", titles)

    def test_similar_returns_max_5_results(self):
        for i in range(6):
            make_check(
                self.user,
                title=f"Facebook militant groups ban extremism report {i}",
                label="FAKE",
                news_source=self.buzzfeed,
            )
        response = self.client.get(
            "/api/similar/?title=Facebook militant groups ban&min_sim=0.1"
        )
        self.assertLessEqual(len(response.json()), 5)

    def test_similar_excludes_exact_title(self):
        response = self.client.get(
            "/api/similar/?title=Facebook Continues To Host Militant Groups Despite Ban&min_sim=0.1"
        )
        titles = [item["title"] for item in response.json()]
        self.assertNotIn(
            "Facebook Continues To Host Militant Groups Despite Ban", titles
        )


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication
# ─────────────────────────────────────────────────────────────────────────────


class NewsCheckDeduplicationTest(APITestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    def _post(self, data):
        return self.client.post("/api/predict/", data, format="json")

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_same_article_not_saved_twice(self, _):
        payload = {"title": SAMPLE_TITLE, "text": SAMPLE_TEXT}
        self._post(payload)
        self._post(payload)
        self.assertEqual(NewsCheck.objects.count(), 1)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_second_prediction_returns_from_cache(self, _):
        payload = {"title": SAMPLE_TITLE, "text": SAMPLE_TEXT}
        self._post(payload)
        response = self._post(payload)
        self.assertTrue(response.json()["from_cache"])

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_two_users_same_article_one_db_record(self, _):
        other_user = make_user(email="other@example.com")
        self._post({"title": SAMPLE_TITLE, "text": SAMPLE_TEXT})
        self.client.force_authenticate(user=other_user)
        self._post({"title": SAMPLE_TITLE, "text": SAMPLE_TEXT})
        self.assertEqual(NewsCheck.objects.count(), 1)
        self.assertEqual(NewsCheck.objects.first().users.count(), 2)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_model_not_called_for_cached_article(self, mock_predict):
        payload = {"title": SAMPLE_TITLE, "text": SAMPLE_TEXT}
        self._post(payload)
        self._post(payload)
        mock_predict.assert_called_once()

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_same_user_appears_once_in_history(self, _):
        payload = {"title": SAMPLE_TITLE, "text": SAMPLE_TEXT}
        self._post(payload)
        self._post(payload)
        history = self.client.get("/api/history/").json()["results"]
        self.assertEqual(len(history), 1)
