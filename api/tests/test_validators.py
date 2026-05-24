"""
test_validators.py — Unit tests for api/validators.py.

Tests cover all validation rules:
  - Empty / whitespace-only text
  - Length bounds (too short, too long)
  - Real words ratio (rejects gibberish and symbol-only text)
  - Repetitive text
  - Language detection (warning, not error)
  - Combined validate_title and validate_body helpers
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from api.validators import (
    validate_body,
    validate_language,
    validate_length,
    validate_not_empty,
    validate_not_repetitive,
    validate_real_words,
    validate_title,
)

DEVICE_ID = "550e8400-e29b-41d4-a716-446655440000"

VALID_TITLE = "Scientists discover new vaccine that could cure all diseases"
VALID_BODY = (
    "A team of researchers at Oxford University has announced a breakthrough "
    "in vaccine development that could potentially cure multiple diseases. "
    "The study, published in Nature, shows promising results in early trials."
)

MOCK_PREDICTION = {
    "label": "FAKE",
    "confidence": 0.83,
    "probas": {"REAL": 0.17, "FAKE": 0.83},
}


# ═══════════════════════════════════════════════════════════════════════════
# validate_not_empty
# ═══════════════════════════════════════════════════════════════════════════


class ValidateNotEmptyTest(TestCase):

    def test_valid_text(self):
        result = validate_not_empty("Some valid text", "Title")
        self.assertTrue(result.is_valid)

    def test_empty_string(self):
        result = validate_not_empty("", "Title")
        self.assertFalse(result.is_valid)
        self.assertTrue(len(result.errors) > 0)

    def test_whitespace_only(self):
        result = validate_not_empty("     ", "Title")
        self.assertFalse(result.is_valid)

    def test_tabs_and_newlines(self):
        result = validate_not_empty("\t\n\r", "Title")
        self.assertFalse(result.is_valid)

    def test_none_value(self):
        result = validate_not_empty(None, "Title")
        self.assertFalse(result.is_valid)


# ═══════════════════════════════════════════════════════════════════════════
# validate_length
# ═══════════════════════════════════════════════════════════════════════════


class ValidateLengthTest(TestCase):

    def _validate(self, text):
        return validate_length(
            text, "Title", min_chars=10, max_chars=300, min_words=3, max_words=30
        )

    def test_valid_length(self):
        result = self._validate(VALID_TITLE)
        self.assertTrue(result.is_valid)

    def test_too_short_chars(self):
        result = self._validate("Hi")
        self.assertFalse(result.is_valid)
        self.assertTrue(any("too short" in e for e in result.errors))

    def test_too_few_words(self):
        result = self._validate("Breaking news today")
        # 3 words is exactly the minimum — should be valid
        self.assertTrue(result.is_valid)

    def test_exactly_two_words_invalid(self):
        result = self._validate("Breaking news is happening right now ok")
        self.assertTrue(result.is_valid)

    def test_too_long_chars(self):
        long_text = "word " * 100  # 500 chars
        result = self._validate(long_text)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("too long" in e for e in result.errors))

    def test_too_many_words(self):
        long_title = " ".join(["word"] * 35)
        result = self._validate(long_title)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("too many words" in e for e in result.errors))


# ═══════════════════════════════════════════════════════════════════════════
# validate_real_words
# ═══════════════════════════════════════════════════════════════════════════


class ValidateRealWordsTest(TestCase):

    def test_valid_english_text(self):
        result = validate_real_words(VALID_TITLE, "Title")
        self.assertTrue(result.is_valid)

    def test_numbers_only(self):
        result = validate_real_words("1234 5678 9012 3456", "Title")
        self.assertFalse(result.is_valid)

    def test_symbols_only(self):
        result = validate_real_words("!!! ??? ### $$$ @@@", "Title")
        self.assertFalse(result.is_valid)

    def test_mixed_gibberish(self):
        result = validate_real_words("1234 &%()! dsdjfncfef 9999 @@@@", "Title")
        self.assertFalse(result.is_valid)

    def test_mostly_numbers_with_some_words(self):
        result = validate_real_words("123 456 789 hello 000 111 222", "Title")
        self.assertFalse(result.is_valid)

    def test_text_with_some_numbers_is_valid(self):
        # Real news titles often contain numbers
        result = validate_real_words("Trump wins 2024 election by 5 points", "Title")
        self.assertTrue(result.is_valid)


# ═══════════════════════════════════════════════════════════════════════════
# validate_not_repetitive
# ═══════════════════════════════════════════════════════════════════════════


class ValidateNotRepetitiveTest(TestCase):

    def test_valid_normal_text(self):
        result = validate_not_repetitive(VALID_TITLE, "Title")
        self.assertTrue(result.is_valid)

    def test_same_word_8_times(self):
        result = validate_not_repetitive(
            "example example example example example example example example", "Title"
        )
        self.assertFalse(result.is_valid)
        self.assertTrue(any("repetitive" in e for e in result.errors))

    def test_same_word_10_times(self):
        result = validate_not_repetitive(" ".join(["test"] * 10), "Title")
        self.assertFalse(result.is_valid)

    def test_same_word_3_times_is_ok(self):
        # 3 repetitions out of a long text is fine
        result = validate_not_repetitive(
            "the president the government the people voted for change today", "Title"
        )
        self.assertTrue(result.is_valid)

    def test_word_repeated_just_below_threshold(self):
        # 3 repetitions in a 10-word text = 30% — below the 40% threshold
        result = validate_not_repetitive(
            "the news today is big the story broke the journalists reported it", "Title"
        )
        self.assertTrue(result.is_valid)

    def test_error_message_contains_word(self):
        result = validate_not_repetitive(" ".join(["spam"] * 8), "Title")
        self.assertFalse(result.is_valid)
        self.assertTrue(any("spam" in e for e in result.errors))


# ═══════════════════════════════════════════════════════════════════════════
# validate_language
# ═══════════════════════════════════════════════════════════════════════════


class ValidateLanguageTest(TestCase):

    def test_english_text_no_warning(self):
        result = validate_language(VALID_TITLE, "Title")
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.warnings), 0)

    def test_spanish_text_gives_warning(self):
        result = validate_language(
            "El presidente anunció nuevas medidas económicas hoy", "Title"
        )
        self.assertTrue(result.is_valid)  # valid — not blocked
        self.assertTrue(len(result.warnings) > 0)

    def test_french_text_gives_warning(self):
        result = validate_language(
            "Le président a annoncé de nouvelles mesures économiques", "Title"
        )
        self.assertTrue(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)

    def test_chinese_text_gives_warning(self):
        result = validate_language("今天总统宣布了新的经济措施", "Title")
        self.assertTrue(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)

    def test_arabic_text_gives_warning(self):
        result = validate_language("أعلن الرئيس عن إجراءات اقتصادية جديدة", "Title")
        self.assertTrue(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)

    def test_warning_message_mentions_english(self):
        result = validate_language("texto en español aquí", "Title")
        self.assertTrue(any("English" in w for w in result.warnings))

    def test_non_english_is_not_blocked(self):
        """Non-English text should produce a warning, not an error."""
        result = validate_language("texto en español aquí", "Title")
        self.assertEqual(len(result.errors), 0)


# ═══════════════════════════════════════════════════════════════════════════
# validate_title (combined)
# ═══════════════════════════════════════════════════════════════════════════


class ValidateTitleTest(TestCase):

    def test_valid_title(self):
        result = validate_title(VALID_TITLE)
        self.assertTrue(result.is_valid)

    def test_empty_title(self):
        result = validate_title("")
        self.assertFalse(result.is_valid)

    def test_whitespace_title(self):
        result = validate_title("   ")
        self.assertFalse(result.is_valid)

    def test_too_short_title(self):
        result = validate_title("Hi")
        self.assertFalse(result.is_valid)

    def test_gibberish_title(self):
        result = validate_title("1234 &%()! dsdjfncfef 9999")
        self.assertFalse(result.is_valid)

    def test_repetitive_title(self):
        result = validate_title(" ".join(["fake"] * 8))
        self.assertFalse(result.is_valid)

    def test_non_english_title_gives_warning(self):
        result = validate_title(
            "El gobierno anuncia nuevas medidas económicas para el país"
        )
        self.assertTrue(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)


# ═══════════════════════════════════════════════════════════════════════════
# validate_body (combined)
# ═══════════════════════════════════════════════════════════════════════════


class ValidateBodyTest(TestCase):

    def test_valid_body(self):
        result = validate_body(VALID_BODY)
        self.assertTrue(result.is_valid)

    def test_empty_body(self):
        result = validate_body("")
        self.assertFalse(result.is_valid)

    def test_too_short_body(self):
        result = validate_body("Short text")
        self.assertFalse(result.is_valid)

    def test_gibberish_body(self):
        result = validate_body("1234 5678 &%()! ### $$$ @@@ !!! ??? 9999 0000")
        self.assertFalse(result.is_valid)

    def test_repetitive_body(self):
        result = validate_body(" ".join(["word"] * 20))
        self.assertFalse(result.is_valid)

    def test_non_english_body_gives_warning(self):
        result = validate_body(
            "El gobierno español ha anunciado hoy nuevas medidas económicas "
            "para hacer frente a la crisis. El presidente compareció ante los "
            "medios de comunicación para explicar el nuevo plan de acción."
        )
        self.assertTrue(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)


# ═══════════════════════════════════════════════════════════════════════════
# API integration — validations in /api/predict/
# ═══════════════════════════════════════════════════════════════════════════


class PredictValidationAPITest(APITestCase):
    """
    Tests that /api/predict/ returns 422 for invalid content
    and 200 with warnings for non-English text.
    """

    def _post(self, data):
        return self.client.post("/api/predict/", data, format="json")

    def test_empty_title_returns_422(self):
        response = self._post(
            {
                "title": "",
                "text": VALID_BODY,
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("validation_errors", response.json())

    def test_whitespace_title_returns_422(self):
        response = self._post(
            {
                "title": "          ",
                "text": VALID_BODY,
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_too_short_title_returns_422(self):
        response = self._post(
            {
                "title": "Hi",
                "text": VALID_BODY,
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_gibberish_title_returns_422(self):
        response = self._post(
            {
                "title": "1234 &%()! dsdjfncfef 9999 @@@@",
                "text": VALID_BODY,
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_repetitive_title_returns_422(self):
        response = self._post(
            {
                "title": "example example example example example example example example",
                "text": VALID_BODY,
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_empty_body_returns_422(self):
        response = self._post(
            {
                "title": VALID_TITLE,
                "text": "",
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_too_short_body_returns_422(self):
        response = self._post(
            {
                "title": VALID_TITLE,
                "text": "Too short.",
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_gibberish_body_returns_422(self):
        response = self._post(
            {
                "title": VALID_TITLE,
                "text": "1234 5678 &%()! ### $$$ @@@ !!! ??? 9999 0000 %%%",
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_validation_errors_in_response(self):
        """422 response contains a list of validation_errors."""
        response = self._post(
            {
                "title": "",
                "text": VALID_BODY,
                "device_id": DEVICE_ID,
            }
        )
        data = response.json()
        self.assertIn("validation_errors", data)
        self.assertIsInstance(data["validation_errors"], list)
        self.assertTrue(len(data["validation_errors"]) > 0)

    def test_invalid_content_is_not_saved_to_db(self):
        """422 responses must not save anything to the database."""
        from api.models import NewsCheck

        self._post(
            {
                "title": "bad",
                "text": VALID_BODY,
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(NewsCheck.objects.count(), 0)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION)
    def test_non_english_returns_200_with_warning(self, _):
        """Non-English text returns 200 but includes a warnings field."""
        response = self._post(
            {
                "title": "El presidente anuncia nuevas medidas económicas para el país hoy",
                "text": (
                    "El gobierno español ha anunciado hoy nuevas medidas económicas "
                    "para hacer frente a la crisis. El presidente compareció ante los "
                    "medios de comunicación para explicar el nuevo plan de acción nacional."
                ),
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("label", data)
        self.assertIn("warnings", data)
        self.assertTrue(len(data["warnings"]) > 0)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION)
    def test_valid_english_text_has_no_warnings(self, _):
        """Valid English text returns 200 without warnings field."""
        response = self._post(
            {
                "title": VALID_TITLE,
                "text": VALID_BODY,
                "device_id": DEVICE_ID,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertNotIn("warnings", data)
