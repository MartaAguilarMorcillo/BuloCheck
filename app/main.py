import torch
from fastapi import FastAPI, HTTPException

from app.predictor import model, tokenizer
from app.schemas import NewsRequest, PredictionResponse

app = FastAPI(
    title="BuloCheck API",
    version="2.0.0",
    description="API para clasificación binaria de noticias con Gemma + partial fine-tuning",
)


@app.get("/")
def home():
    return {"message": "BuloCheck API funcionando"}


@app.post("/predict", response_model=PredictionResponse)
def predict_news(request: NewsRequest):
    try:
        full_text = f"{request.title}\n{request.text}"

        inputs = tokenizer(
            full_text,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=512,
        )

        with torch.no_grad():
            logits = model(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"]
            )

            probs = torch.softmax(logits, dim=1)
            prediction = torch.argmax(probs, dim=1).item()
            confidence = probs[0][prediction].item()

        label = "FAKE" if prediction == 1 else "REAL"

        return PredictionResponse(
            label=label,
            prediction=prediction,
            confidence=round(confidence, 4)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
