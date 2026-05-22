"""
validators.py — Content validation for news title and body text.

Validates that the input text is suitable for fake news classification:
  - Not empty or whitespace-only
  - Within acceptable length bounds
  - Contains real words (not random characters or numbers)
  - Not repetitive (same word repeated excessively)
  - Detects non-English text and returns a warning (does not block)
"""

import re
from dataclasses import dataclass, field

# ── Validation thresholds ──────────────────────────────────────────────────

TITLE_MIN_WORDS = 3
TITLE_MAX_WORDS = 30
TITLE_MIN_CHARS = 10
TITLE_MAX_CHARS = 300

BODY_MIN_WORDS = 10
BODY_MAX_WORDS = 600
BODY_MIN_CHARS = 40
BODY_MAX_CHARS = 8000

# Max ratio of a single word repetitions over total words
MAX_REPETITION_RATIO = 0.4  # if one word is >40% of all words → repetitive

# Min ratio of real alphabetic words over all tokens
MIN_ALPHA_RATIO = 0.5  # at least 50% of tokens must be real words

# Common non-English characters that suggest non-English text
NON_ENGLISH_PATTERNS = [
    r"[àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]",  # French, Spanish, Portuguese
    r"[αβγδεζηθικλμνξοπρστυφχψω]",  # Greek
    r"[абвгдеёжзийклмнопрстуфхцчшщъыьэюя]",  # Cyrillic
    r"[\u4e00-\u9fff]",  # Chinese
    r"[\u3040-\u309f\u30a0-\u30ff]",  # Japanese
    r"[\uac00-\ud7af]",  # Korean
    r"[\u0600-\u06ff]",  # Arabic
    r"[\u0900-\u097f]",  # Hindi/Devanagari
]

NON_ENGLISH_REGEX = re.compile("|".join(NON_ENGLISH_PATTERNS), re.IGNORECASE)


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def _tokenize(text: str) -> list:
    """Split text into lowercase word tokens."""
    return re.findall(r"\b[a-zA-Z']+\b", text.lower())


def _count_all_tokens(text: str) -> list:
    """Split text into all tokens including numbers and symbols."""
    return text.strip().split()


def validate_not_empty(text: str, field_name: str) -> ValidationResult:
    """Text must not be empty or whitespace-only."""
    if not text or not text.strip():
        return ValidationResult(
            is_valid=False,
            errors=[f"{field_name} must not be empty or contain only spaces."],
        )
    return ValidationResult(is_valid=True)


def validate_length(
    text: str,
    field_name: str,
    min_chars: int,
    max_chars: int,
    min_words: int,
    max_words: int,
) -> ValidationResult:
    """Text must be within acceptable character and word length bounds."""
    stripped = text.strip()
    char_count = len(stripped)
    word_count = len(_tokenize(stripped))
    errors = []

    if char_count < min_chars:
        errors.append(
            f"{field_name} is too short ({char_count} chars). "
            f"Minimum is {min_chars} characters."
        )
    if char_count > max_chars:
        errors.append(
            f"{field_name} is too long ({char_count} chars). "
            f"Maximum is {max_chars} characters."
        )
    if word_count < min_words:
        errors.append(
            f"{field_name} has too few words ({word_count}). "
            f"Minimum is {min_words} words."
        )
    if word_count > max_words:
        errors.append(
            f"{field_name} has too many words ({word_count}). "
            f"Maximum is {max_words} words."
        )

    return ValidationResult(is_valid=len(errors) == 0, errors=errors)


def validate_real_words(text: str, field_name: str) -> ValidationResult:
    """
    Text must contain a minimum ratio of real alphabetic words.
    Rejects inputs like '1234 &%()! dsdjfncfef' or '!!! ??? ###'.
    """
    all_tokens = _count_all_tokens(text)
    if not all_tokens:
        return ValidationResult(
            is_valid=False,
            errors=[f"{field_name} does not contain valid words."],
        )

    alpha_tokens = _tokenize(text)
    alpha_ratio = len(alpha_tokens) / len(all_tokens)

    if alpha_ratio < MIN_ALPHA_RATIO:
        return ValidationResult(
            is_valid=False,
            errors=[
                f"{field_name} does not appear to contain valid text. "
                f"Please enter a real news {field_name.lower()}."
            ],
        )

    return ValidationResult(is_valid=True)


def validate_not_repetitive(text: str, field_name: str) -> ValidationResult:
    """
    Text must not consist of the same word repeated excessively.
    Rejects: 'example example example example example example example'
    """
    words = _tokenize(text)
    if not words:
        return ValidationResult(is_valid=True)

    word_counts = {}
    for word in words:
        word_counts[word] = word_counts.get(word, 0) + 1

    most_common_word = max(word_counts, key=word_counts.get)
    most_common_count = word_counts[most_common_word]
    repetition_ratio = most_common_count / len(words)

    if repetition_ratio > MAX_REPETITION_RATIO and most_common_count >= 4:
        return ValidationResult(
            is_valid=False,
            errors=[
                f"{field_name} appears to be repetitive. "
                f"The word '{most_common_word}' is repeated {most_common_count} times."
            ],
        )

    return ValidationResult(is_valid=True)


def validate_language(text: str, field_name: str) -> ValidationResult:
    """
    Detects non-English characters and returns a WARNING (not an error).
    The model was trained on English text but may generalise to other languages
    due to Gemma's multilingual pre-training. We warn but do not block.
    """
    if NON_ENGLISH_REGEX.search(text):
        return ValidationResult(
            is_valid=True,  # valid — we don't block, just warn
            warnings=[
                f"{field_name} appears to contain non-English text. "
                "The model was trained on English news articles. "
                "Predictions for other languages may be less accurate."
            ],
        )
    return ValidationResult(is_valid=True)


def validate_text_field(
    text: str,
    field_name: str,
    min_chars: int,
    max_chars: int,
    min_words: int,
    max_words: int,
) -> ValidationResult:
    """
    Run all validations on a text field and aggregate results.
    Returns a single ValidationResult with all errors and warnings combined.
    """
    all_errors = []
    all_warnings = []

    checks = [
        validate_not_empty(text, field_name),
        validate_length(text, field_name, min_chars, max_chars, min_words, max_words),
        validate_real_words(text, field_name),
        validate_not_repetitive(text, field_name),
        validate_language(text, field_name),
    ]

    # Stop at first blocking error (empty check) to avoid misleading messages
    if not checks[0].is_valid:
        return checks[0]

    for result in checks[1:]:
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)

    return ValidationResult(
        is_valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings,
    )


def validate_title(title: str) -> ValidationResult:
    """Validate news title."""
    return validate_text_field(
        title,
        "Title",
        min_chars=TITLE_MIN_CHARS,
        max_chars=TITLE_MAX_CHARS,
        min_words=TITLE_MIN_WORDS,
        max_words=TITLE_MAX_WORDS,
    )


def validate_body(body: str) -> ValidationResult:
    """Validate news body text."""
    return validate_text_field(
        body,
        "Body",
        min_chars=BODY_MIN_CHARS,
        max_chars=BODY_MAX_CHARS,
        min_words=BODY_MIN_WORDS,
        max_words=BODY_MAX_WORDS,
    )
