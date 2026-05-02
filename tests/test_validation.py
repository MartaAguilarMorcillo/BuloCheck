from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# PYDANTIC VALIDATIONS (422)


def test_title_too_short():
    response = client.post(
        "/predict",
        json={"title": "Hi", "text": "This is a valid enough article text."},
    )

    assert response.status_code == 422


def test_text_too_short():
    response = client.post(
        "/predict",
        json={"title": "Valid title", "text": "Too short"},
    )

    assert response.status_code == 422


def test_title_too_long():
    response = client.post(
        "/predict",
        json={"title": "A" * 301, "text": "This is a valid enough article text."},
    )

    assert response.status_code == 422


def test_text_too_long():
    response = client.post(
        "/predict",
        json={"title": "Valid title", "text": "A" * 5001},
    )

    assert response.status_code == 422


# CUSTOM VALIDATIONS (400)


def test_empty_text():
    response = client.post(
        "/predict",
        json={"title": "Valid title", "text": "                    abc"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Text not meaningful"


def test_meaningless_text():
    response = client.post(
        "/predict",
        json={"title": "Random symbols", "text": "123456789 $$$$$ !!!!! ?????"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Text not meaningful"


def test_repetitive_text():
    response = client.post(
        "/predict",
        json={
            "title": "Spam",
            "text": (
                "fake fake fake fake fake fake fake fake "
                "fake fake fake fake fake fake fake fake"
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Repetitive content detected"


def test_non_english_text():
    response = client.post(
        "/predict",
        json={
            "title": "Noticias",
            "text": (
                "Esta noticia está completamente escrita "
                "en español para probar el detector."
            ),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only English supported"
