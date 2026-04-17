from pydantic import BaseModel, Field


class NewsRequest(BaseModel):
    title: str = Field(..., min_length=3, description="Título de la noticia")
    text: str = Field(
        ..., min_length=20, description="Contenido principal de la noticia"
    )


class PredictionResponse(BaseModel):
    label: str
    prediction: int
    confidence: float
