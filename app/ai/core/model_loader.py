import threading

from sentence_transformers import SentenceTransformer

from app.ai.core.config import EMBEDDING_MODEL_NAME


_model = None
_lock = threading.Lock()


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                print("[AI] Loading embedding model...")
                _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
                print("[AI] Model loaded successfully")
    return _model
