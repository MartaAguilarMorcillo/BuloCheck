"""
test_integration.py — Integration tests: full request → DB → response flow.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import NewsCheck

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


class FullFlowIntegrationTest(APITestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_then_history(self, _):
        predict_response = self.client.post(
            "/api/predict/",
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "domain": "bbc.com",
            },
            format="json",
        )

        self.assertEqual(predict_response.status_code, status.HTTP_200_OK)
        self.assertEqual(predict_response.json()["label"], "FAKE")

        history_response = self.client.get("/api/history/")
        self.assertEqual(history_response.status_code, status.HTTP_200_OK)

        history = history_response.json()["results"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["title"], SAMPLE_TITLE)
        self.assertEqual(history[0]["label"], "FAKE")
        self.assertEqual(history[0]["news_source"]["domain"], "bbc.com")

    @patch("api.views.predict_news")
    def test_predict_then_sources_ranking(self, mock_predict):
        mock_predict.return_value = MOCK_PREDICTION_REAL
        for _ in range(2):
            self.client.post(
                "/api/predict/",
                {
                    "title": SAMPLE_TITLE,
                    "text": SAMPLE_TEXT,
                    "domain": "nytimes.com",
                },
                format="json",
            )

        mock_predict.return_value = MOCK_PREDICTION_FAKE
        self.client.post(
            "/api/predict/",
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "domain": "foxnews.com",
            },
            format="json",
        )

        sources_response = self.client.get("/api/sources/")
        self.assertEqual(sources_response.status_code, status.HTTP_200_OK)
        data = sources_response.json()
        self.assertEqual(data[0]["news_source"]["domain"], "nytimes.com")
        self.assertEqual(data[1]["news_source"]["domain"], "foxnews.com")

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_multiple_users_data_isolation(self, _):
        other_user = make_user(email="other@example.com")

        self.client.post(
            "/api/predict/",
            {
                "title": "User one reads breaking news about the economy today",
                "text": SAMPLE_TEXT,
                "domain": "bbc.com",
            },
            format="json",
        )

        self.client.force_authenticate(user=other_user)
        self.client.post(
            "/api/predict/",
            {
                "title": "User two reads breaking news about politics this week",
                "text": SAMPLE_TEXT,
                "domain": "cnn.com",
            },
            format="json",
        )

        self.client.force_authenticate(user=self.user)
        history_1 = self.client.get("/api/history/").json()["results"]
        titles_1 = [item["title"] for item in history_1]
        self.assertIn("User one reads breaking news about the economy today", titles_1)
        self.assertNotIn(
            "User two reads breaking news about politics this week", titles_1
        )

        self.client.force_authenticate(user=other_user)
        history_2 = self.client.get("/api/history/").json()["results"]
        titles_2 = [item["title"] for item in history_2]
        self.assertIn("User two reads breaking news about politics this week", titles_2)
        self.assertNotIn(
            "User one reads breaking news about the economy today", titles_2
        )

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_check_id_matches_db_record(self, _):
        response = self.client.post(
            "/api/predict/",
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
            },
            format="json",
        )

        check_id = response.json()["check_id"]
        db_check = NewsCheck.objects.get(id=check_id)
        self.assertEqual(db_check.label, "FAKE")
        self.assertEqual(db_check.title, SAMPLE_TITLE)

    @patch("api.views.predict_news", side_effect=Exception("Space is sleeping"))
    def test_model_error_does_not_save_to_db(self, _):
        self.client.post(
            "/api/predict/",
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
            },
            format="json",
        )
        self.assertEqual(NewsCheck.objects.count(), 0)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_same_user_multiple_predictions(self, _):
        titles = [
            "Scientists discover new evidence of climate change in Arctic region",
            "Government announces major economic reform plan for next year",
            "Technology company launches revolutionary artificial intelligence product",
            "Sports team wins championship after decades of unsuccessful attempts",
            "Health experts warn about new virus spreading across multiple countries",
        ]

        for title in titles:
            self.client.post(
                "/api/predict/",
                {
                    "title": title,
                    "text": SAMPLE_TEXT,
                },
                format="json",
            )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(NewsCheck.objects.count(), 5)

        history = self.client.get("/api/history/").json()["results"]
        self.assertEqual(len(history), 5)

    @patch("api.views.predict_news")
    def test_sources_empty_before_any_prediction(self, _):
        response = self.client.get("/api/sources/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])
