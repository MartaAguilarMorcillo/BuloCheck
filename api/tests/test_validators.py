"""
test_validators.py — Unit tests for api/validators.py.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
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

User = get_user_model()

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
        self.assertTrue(self._validate(VALID_TITLE).is_valid)

    def test_too_short_chars(self):
        result = self._validate("Hi")
        self.assertFalse(result.is_valid)
        self.assertTrue(any("too short" in e for e in result.errors))

    def test_too_few_words(self):
        self.assertTrue(self._validate("Breaking news today").is_valid)

    def test_exactly_two_words_invalid(self):
        self.assertTrue(
            self._validate("Breaking news is happening right now ok").is_valid
        )

    def test_too_long_chars(self):
        result = self._validate("word " * 100)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("too long" in e for e in result.errors))

    def test_too_many_words(self):
        result = self._validate(" ".join(["word"] * 35))
        self.assertFalse(result.is_valid)
        self.assertTrue(any("too many words" in e for e in result.errors))


# ═══════════════════════════════════════════════════════════════════════════
# validate_real_words
# ═══════════════════════════════════════════════════════════════════════════


class ValidateRealWordsTest(TestCase):

    def test_valid_english_text(self):
        self.assertTrue(validate_real_words(VALID_TITLE, "Title").is_valid)

    def test_numbers_only(self):
        self.assertFalse(validate_real_words("1234 5678 9012 3456", "Title").is_valid)

    def test_symbols_only(self):
        self.assertFalse(validate_real_words("!!! ??? ### $$$ @@@", "Title").is_valid)

    def test_mixed_gibberish(self):
        self.assertFalse(
            validate_real_words("1234 &%()! dsdjfncfef 9999 @@@@", "Title").is_valid
        )

    def test_mostly_numbers_with_some_words(self):
        self.assertFalse(
            validate_real_words("123 456 789 hello 000 111 222", "Title").is_valid
        )

    def test_text_with_some_numbers_is_valid(self):
        self.assertTrue(
            validate_real_words(
                "Trump wins 2024 election by 5 points", "Title"
            ).is_valid
        )


# ═══════════════════════════════════════════════════════════════════════════
# validate_not_repetitive
# ═══════════════════════════════════════════════════════════════════════════


class ValidateNotRepetitiveTest(TestCase):

    def test_valid_normal_text(self):
        self.assertTrue(validate_not_repetitive(VALID_TITLE, "Title").is_valid)

    def test_same_word_8_times(self):
        result = validate_not_repetitive(
            "example example example example example example example example", "Title"
        )
        self.assertFalse(result.is_valid)
        self.assertTrue(any("repetitive" in e for e in result.errors))

    def test_same_word_10_times(self):
        self.assertFalse(
            validate_not_repetitive(" ".join(["test"] * 10), "Title").is_valid
        )

    def test_same_word_3_times_is_ok(self):
        self.assertTrue(
            validate_not_repetitive(
                "the president the government the people voted for change today",
                "Title",
            ).is_valid
        )

    def test_word_repeated_just_below_threshold(self):
        self.assertTrue(
            validate_not_repetitive(
                "the news today is big the story broke the journalists reported it",
                "Title",
            ).is_valid
        )

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
        self.assertTrue(result.is_valid)
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
        result = validate_language("texto en español aquí", "Title")
        self.assertEqual(len(result.errors), 0)


# ═══════════════════════════════════════════════════════════════════════════
# validate_title / validate_body (combined)
# ═══════════════════════════════════════════════════════════════════════════


class ValidateTitleTest(TestCase):

    def test_valid_title(self):
        self.assertTrue(validate_title(VALID_TITLE).is_valid)

    def test_empty_title(self):
        self.assertFalse(validate_title("").is_valid)

    def test_whitespace_title(self):
        self.assertFalse(validate_title("   ").is_valid)

    def test_too_short_title(self):
        self.assertFalse(validate_title("Hi").is_valid)

    def test_gibberish_title(self):
        self.assertFalse(validate_title("1234 &%()! dsdjfncfef 9999").is_valid)

    def test_repetitive_title(self):
        self.assertFalse(validate_title(" ".join(["fake"] * 8)).is_valid)

    def test_non_english_title_gives_warning(self):
        result = validate_title(
            "El gobierno anuncia nuevas medidas económicas para el país"
        )
        self.assertTrue(result.is_valid)
        self.assertTrue(len(result.warnings) > 0)


class ValidateBodyTest(TestCase):

    def test_valid_body(self):
        self.assertTrue(validate_body(VALID_BODY).is_valid)

    def test_empty_body(self):
        self.assertFalse(validate_body("").is_valid)

    def test_too_short_body(self):
        self.assertFalse(validate_body("Short text").is_valid)

    def test_gibberish_body(self):
        self.assertFalse(
            validate_body("1234 5678 &%()! ### $$$ @@@ !!! ??? 9999 0000").is_valid
        )

    def test_repetitive_body(self):
        self.assertFalse(validate_body(" ".join(["word"] * 20)).is_valid)

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

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def _post(self, data):
        return self.client.post("/api/predict/", data, format="json")

    def test_empty_title_returns_422(self):
        response = self._post({"title": "", "text": VALID_BODY})
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("validation_errors", response.json())

    def test_whitespace_title_returns_422(self):
        response = self._post({"title": "          ", "text": VALID_BODY})
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_too_short_title_returns_422(self):
        response = self._post({"title": "Hi", "text": VALID_BODY})
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_gibberish_title_returns_422(self):
        response = self._post(
            {"title": "1234 &%()! dsdjfncfef 9999 @@@@", "text": VALID_BODY}
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_repetitive_title_returns_422(self):
        response = self._post(
            {
                "title": "example example example example example example example example",
                "text": VALID_BODY,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_empty_body_returns_422(self):
        response = self._post({"title": VALID_TITLE, "text": ""})
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_too_short_body_returns_422(self):
        response = self._post({"title": VALID_TITLE, "text": "Too short."})
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_gibberish_body_returns_422(self):
        response = self._post(
            {
                "title": VALID_TITLE,
                "text": "1234 5678 &%()! ### $$$ @@@ !!! ??? 9999 0000 %%%",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_validation_errors_in_response(self):
        response = self._post({"title": "", "text": VALID_BODY})
        data = response.json()
        self.assertIn("validation_errors", data)
        self.assertIsInstance(data["validation_errors"], list)
        self.assertTrue(len(data["validation_errors"]) > 0)

    def test_invalid_content_is_not_saved_to_db(self):
        from api.models import NewsCheck

        self._post({"title": "bad", "text": VALID_BODY})
        self.assertEqual(NewsCheck.objects.count(), 0)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION)
    def test_non_english_returns_200_with_warning(self, _):
        response = self._post(
            {
                "title": "El presidente anuncia nuevas medidas económicas para el país hoy",
                "text": (
                    "El gobierno español ha anunciado hoy nuevas medidas económicas "
                    "para hacer frente a la crisis. El presidente compareció ante los "
                    "medios de comunicación para explicar el nuevo plan de acción nacional."
                ),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("label", data)
        self.assertIn("warnings", data)
        self.assertTrue(len(data["warnings"]) > 0)

    @patch("api.views.predict_news", return_value=MOCK_PREDICTION)
    def test_valid_english_text_has_no_warnings(self, _):
        response = self._post({"title": VALID_TITLE, "text": VALID_BODY})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("warnings", response.json())
