from fastapi import FastAPI

app = FastAPI(title="Fake News Detection API", version="1.0.0")


@app.get("/")
def home():
    return {"message": "API working"}
