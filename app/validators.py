import re

from fastapi import HTTPException
from langdetect import detect


def validate_text_not_empty(text: str):
    if not text.strip():
        raise HTTPException(status_code=400, detail="Empty text")


def validate_text_length(text: str, max_length: int = 5000):
    if len(text) > max_length:
        raise HTTPException(status_code=400, detail="Text too long")


def validate_meaningful_text(text: str):
    letters = len(re.findall(r"[a-zA-Z]", text))
    total = len(text)

    if total == 0 or letters / total < 0.3:
        raise HTTPException(status_code=400, detail="Text not meaningful")


def validate_repetitive_text(text: str):
    words = text.split()

    if len(words) > 0 and len(set(words)) < len(words) * 0.3:
        raise HTTPException(status_code=400, detail="Repetitive content detected")


def validate_language(text: str, lang: str = "en"):
    if detect(text) != lang:
        raise HTTPException(status_code=400, detail="Only English supported")
