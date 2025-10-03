from __future__ import annotations
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # мультиязык
_model = None


def load_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_text(title: str, content: str, max_body_chars: int = 600) -> np.ndarray:
    text = (title or "").strip() + " [SEP] " + (content or "")[:max_body_chars].strip()
    model = load_model()
    v = model.encode([text], normalize_embeddings=True)[0]
    return v.astype(np.float32)