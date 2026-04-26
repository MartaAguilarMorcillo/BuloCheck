from pydantic import BaseModel, Field


class NewsRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=300)
    text: str = Field(..., min_length=20, max_length=5000)


class PredictionResponse(BaseModel):
    label: str
    prediction: int
    confidence: float
