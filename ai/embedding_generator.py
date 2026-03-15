from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, List

from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(settings.RESUME_EMBEDDING_MODEL)


@dataclass(frozen=True)
class EmbeddingInput:
    section: str
    content: str


class EmbeddingGenerator:
    def generate(self, items: Iterable[EmbeddingInput]) -> List[dict]:
        materialized = [i for i in items if i.content and i.content.strip()]
        if not materialized:
            return []

        model = _get_model()
        texts = [i.content for i in materialized]
        vectors = model.encode(texts, normalize_embeddings=True)

        out: List[dict] = []
        for embedding_input, vec in zip(materialized, vectors):
            out.append(
                {
                    "section": embedding_input.section,
                    "content": embedding_input.content,
                    "embedding": vec.tolist() if hasattr(vec, "tolist") else list(vec),
                }
            )
        return out
