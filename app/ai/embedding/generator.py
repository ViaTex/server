from app.ai.core.model_loader import get_embedding_model


def generate_embedding(text: str) -> list[float]:
    model = get_embedding_model()
    vector = model.encode(text or "", normalize_embeddings=True)
    return vector.tolist()
