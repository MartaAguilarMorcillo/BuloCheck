"""
test_ml.py — Unit tests for ml.py (predict_news and get_client).
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

import api.ml as ml_module

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


class MLPredictNewsUnitTest(TestCase):
    """Unit tests for ml.predict_news() isolating the gradio_client call."""

    @patch("api.ml.get_client")
    def test_predict_returns_fake_label(self, mock_get_client):
        """predict_news returns correct structure when model says FAKE."""
        mock_client = MagicMock()
        mock_client.predict.return_value = MOCK_PREDICTION_FAKE
        mock_get_client.return_value = mock_client

        from api.ml import predict_news

        result = predict_news(SAMPLE_TITLE, SAMPLE_TEXT)

        self.assertEqual(result["label"], "FAKE")
        self.assertAlmostEqual(result["confidence"], 0.8367)
        self.assertIn("probas", result)
        self.assertIn("REAL", result["probas"])
        self.assertIn("FAKE", result["probas"])

    @patch("api.ml.get_client")
    def test_predict_returns_real_label(self, mock_get_client):
        """predict_news returns correct structure when model says REAL."""
        mock_client = MagicMock()
        mock_client.predict.return_value = MOCK_PREDICTION_REAL
        mock_get_client.return_value = mock_client

        from api.ml import predict_news

        result = predict_news(SAMPLE_TITLE, SAMPLE_TEXT)

        self.assertEqual(result["label"], "REAL")
        self.assertAlmostEqual(result["confidence"], 0.7512)

    @patch("api.ml.get_client")
    def test_predict_calls_correct_api_name(self, mock_get_client):
        """predict_news calls the Space with api_name='/api_predict'."""
        mock_client = MagicMock()
        mock_client.predict.return_value = MOCK_PREDICTION_REAL
        mock_get_client.return_value = mock_client

        from api.ml import predict_news

        predict_news(SAMPLE_TITLE, SAMPLE_TEXT)

        call_kwargs = mock_client.predict.call_args
        self.assertIn("/api_predict", str(call_kwargs))

    @patch("api.ml.get_client")
    def test_predict_sends_title_and_text(self, mock_get_client):
        """predict_news sends title and text as separate arguments."""
        mock_client = MagicMock()
        mock_client.predict.return_value = MOCK_PREDICTION_REAL
        mock_get_client.return_value = mock_client

        from api.ml import predict_news

        predict_news("My Title", "My Body Text")

        args = mock_client.predict.call_args[0]
        self.assertEqual(args[0], "My Title")
        self.assertEqual(args[1], "My Body Text")

    def test_get_client_singleton(self):
        """get_client returns the same instance on multiple calls."""
        ml_module._client = None  # reset singleton

        with patch("api.ml.Client") as mock_client_class:
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance

            from api.ml import get_client

            client1 = get_client()
            client2 = get_client()

            # Client() constructor called only once
            mock_client_class.assert_called_once()
            self.assertEqual(client1, client2)
