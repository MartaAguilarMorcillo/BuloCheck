"""
ml.py — Conexión con el HuggingFace Space usando gradio_client.
"""
from gradio_client import Client

_client = None

def get_client():
    global _client
    if _client is None:
        _client = Client(
            "MartaAguilarMorcillo/fakenews-api",
            httpx_kwargs={"timeout": 180}  # 3 minutos — suficiente para que el Space despierte 
        )
    return _client


def predict_news(title: str, text: str) -> dict:
    client = get_client()

    result = client.predict(
        title,
        text,
        api_name="/api_predict",
    )

    return {
        "label": result["label"],
        "confidence": result["confidence"],
        "probas": result["probas"],
    }