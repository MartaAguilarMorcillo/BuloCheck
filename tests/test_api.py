from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_predict_valid_news():
    response = client.post(
        "/predict",
        json={
            "title": "Breaking News",
            "text": (
                "This is a meaningful English article with enough "
                "content to pass all validations."
            ),
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "label" in data
    assert "prediction" in data
    assert "confidence" in data
