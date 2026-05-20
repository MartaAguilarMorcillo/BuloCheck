"""
test_integration.py — Integration tests: full request → DB → response flow.
"""

import uuid
from unittest.mock import patch  # ← corregido: era 'patchf'

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


class FullFlowIntegrationTest(APITestCase):

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_predict_then_history(self, _):
        predict_response = self.client.post(
            "/api/predict/",
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "source": "bbc.com",
                "device_id": DEVICE_ID,
            },
            format="json",
        )

        self.assertEqual(predict_response.status_code, status.HTTP_200_OK)
        self.assertEqual(predict_response.json()["label"], "FAKE")

        history_response = self.client.get("/api/history/", HTTP_X_DEVICE_ID=DEVICE_ID)
        self.assertEqual(history_response.status_code, status.HTTP_200_OK)

        history = history_response.json()["results"]  # ← corregido
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["title"], SAMPLE_TITLE)
        self.assertEqual(history[0]["label"], "FAKE")
        self.assertEqual(history[0]["source"], "bbc.com")

    @patch("api.views.predict_news")
    def test_predict_then_sources_ranking(self, mock_predict):
        mock_predict.return_value = MOCK_PREDICTION_REAL
        for _ in range(2):
            self.client.post(
                "/api/predict/",
                {
                    "title": SAMPLE_TITLE,
                    "text": SAMPLE_TEXT,
                    "source": "nytimes.com",
                    "device_id": DEVICE_ID,
                },
                format="json",
            )

        mock_predict.return_value = MOCK_PREDICTION_FAKE
        self.client.post(
            "/api/predict/",
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "source": "foxnews.com",
                "device_id": DEVICE_ID,
            },
            format="json",
        )

        sources_response = self.client.get("/api/sources/", HTTP_X_DEVICE_ID=DEVICE_ID)
        self.assertEqual(sources_response.status_code, status.HTTP_200_OK)
        data = sources_response.json()
        self.assertEqual(data[0]["source"], "nytimes.com")
        self.assertEqual(data[1]["source"], "foxnews.com")

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_multiple_users_data_isolation(self, _):
        device_id_2 = str(uuid.uuid4())

        self.client.post(
            "/api/predict/",
            {
                "title": "User 1 news",
                "text": SAMPLE_TEXT,
                "source": "bbc.com",
                "device_id": DEVICE_ID,
            },
            format="json",
        )

        self.client.post(
            "/api/predict/",
            {
                "title": "User 2 news",
                "text": SAMPLE_TEXT,
                "source": "cnn.com",
                "device_id": device_id_2,
            },
            format="json",
        )

        history_1 = self.client.get("/api/history/", HTTP_X_DEVICE_ID=DEVICE_ID).json()[
            "results"
        ]  # ← corregido
        titles_1 = [item["title"] for item in history_1]
        self.assertIn("User 1 news", titles_1)
        self.assertNotIn("User 2 news", titles_1)

        history_2 = self.client.get(
            "/api/history/", HTTP_X_DEVICE_ID=device_id_2
        ).json()[
            "results"
        ]  # ← corregido
        titles_2 = [item["title"] for item in history_2]
        self.assertIn("User 2 news", titles_2)
        self.assertNotIn("User 1 news", titles_2)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_check_id_matches_db_record(self, _):
        response = self.client.post(
            "/api/predict/",
            {
                "title": SAMPLE_TITLE,
                "text": SAMPLE_TEXT,
                "device_id": DEVICE_ID,
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
                "device_id": DEVICE_ID,
            },
            format="json",
        )

        self.assertEqual(NewsCheck.objects.count(), 0)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION_FAKE)
    def test_same_user_multiple_predictions(self, _):
        for i in range(5):
            self.client.post(
                "/api/predict/",
                {
                    "title": f"News article {i}",
                    "text": SAMPLE_TEXT,
                    "device_id": DEVICE_ID,
                },
                format="json",
            )

        self.assertEqual(AnonymousUser.objects.count(), 1)
        self.assertEqual(NewsCheck.objects.count(), 5)

        history = self.client.get("/api/history/", HTTP_X_DEVICE_ID=DEVICE_ID).json()[
            "results"
        ]  # ← corregido
        self.assertEqual(len(history), 5)

    @patch("api.views.predict_news")
    def test_sources_empty_before_any_prediction(self, _):
        response = self.client.get("/api/sources/", HTTP_X_DEVICE_ID=DEVICE_ID)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])
