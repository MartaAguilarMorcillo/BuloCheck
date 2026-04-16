import os
import torch
from huggingface_hub import login
from transformers import AutoModel, AutoTokenizer

from app.model import GemmaForFakeNewsClassification

HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
if HF_TOKEN:
    login(token=HF_TOKEN)

MODEL_DIR = "app/gemma_fake_news_adapter"

# ==========================
# Cargar pesos parciales
# ==========================
partial = torch.load(
    os.path.join(MODEL_DIR, "partial_weights.pt"),
    map_location="cpu"
)

config = partial["config"]

# ==========================
# Tokenizer
# ==========================
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

# ==========================
# Modelo base desde HF
# ==========================
base_model = AutoModel.from_pretrained(
    config["model_name"],
    torch_dtype=torch.float32
)

# ==========================
# Reconstrucción modelo
# ==========================
model = GemmaForFakeNewsClassification(
    base_model=base_model,
    hidden_size=config["hidden_size"],
    num_classes=config["num_classes"]
)

N = config["num_unfrozen_layers"]

# Cargar últimas 5 capas fine-tuned
model.base_model.layers[-N:].load_state_dict(partial["last_layers"])

# Cargar classifier
model.classifier.load_state_dict(partial["classifier"])

model.eval()