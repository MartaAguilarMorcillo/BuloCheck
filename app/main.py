import torch
from fastapi import FastAPI, HTTPException

from app.predictor import device, model, tokenizer
from app.schemas import NewsRequest, PredictionResponse
from app.validators import (
    validate_language,
    validate_meaningful_text,
    validate_repetitive_text,
    validate_text_length,
    validate_text_not_empty,
)

app = FastAPI(
    title="BuloCheck API",
    version="2.1.0",
)


@app.post("/predict", response_model=PredictionResponse)
def predict_news(request: NewsRequest):
    try:
        text = request.text

        # VALIDATIONS
        validate_text_not_empty(text)
        validate_text_length(text)
        validate_meaningful_text(text)
        validate_repetitive_text(text)
        validate_language(text)

        # INFERENCE
        full_text = f"{request.title}\n{text}"

        inputs = tokenizer(
            full_text,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=512,
        )

        inputs = {k: v.to(device) for k, v in inputs.items()}

        model.eval()

        with torch.inference_mode():
            logits = model(**inputs)

        probs = torch.softmax(logits, dim=1)
        prediction = torch.argmax(probs, dim=1).item()
        confidence = probs[0][prediction].item()

        return PredictionResponse(
            label="FAKE" if prediction == 1 else "REAL",
            prediction=prediction,
            confidence=round(confidence, 4),
        )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(status_code=500, detail="Model inference failed")
