"""Topic Librarian service.

Converts dynamic topic strings into 384-dimension vectors using a local
SentenceTransformer model and maps them to the ``topics`` table via HNSW
cosine-distance search (synonym gate → parent hierarchy gate → insert).
"""

from __future__ import annotations

import logging
import uuid
from typing import List

from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.topic import Topic

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-loaded singleton for the embedding model
# ---------------------------------------------------------------------------
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Return (and cache) the SentenceTransformer model instance."""
    global _model
    if _model is None:
        logger.info("Loading topic embedding model: %s", settings.TOPIC_EMBEDDING_MODEL)
        _model = SentenceTransformer(settings.TOPIC_EMBEDDING_MODEL)
    return _model


# ---------------------------------------------------------------------------
# Gate helpers
# ---------------------------------------------------------------------------

# Cosine-distance thresholds
_SYNONYM_THRESHOLD = 0.05
_PARENT_THRESHOLD = 0.30


def _embed(topic: str) -> list[float]:
    """Encode a single topic string into a 384-dim float vector."""
    model = _get_model()
    vector = model.encode(topic, normalize_embeddings=True)
    return vector.tolist()


def _find_synonym(db: Session, vec_literal: str) -> str | None:
    """Gate 1 — return UUID of an existing topic within synonym distance."""
    row = db.execute(
        text(
            "SELECT id, embedding <=> :vec AS distance "
            "FROM topics "
            "ORDER BY embedding <=> :vec "
            "LIMIT 1"
        ),
        {"vec": vec_literal},
    ).first()

    if row is not None and row.distance < _SYNONYM_THRESHOLD:
        return str(row.id)
    return None


def _find_parent(db: Session, vec_literal: str) -> str | None:
    """Gate 2 — return UUID of the closest root-level topic within parent distance."""
    row = db.execute(
        text(
            "SELECT id, embedding <=> :vec AS distance "
            "FROM topics "
            "WHERE parent_id IS NULL "
            "ORDER BY embedding <=> :vec "
            "LIMIT 1"
        ),
        {"vec": vec_literal},
    ).first()

    if row is not None and row.distance < _PARENT_THRESHOLD:
        return str(row.id)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def process_and_map_dynamic_topics(
    dynamic_topics: list[str],
    db: Session,
) -> List[str]:
    """Map each dynamic topic string to a UUID in the ``topics`` table.

    Workflow per topic:
      1. Embed → 384-dim vector.
      2. Gate 1 (synonym):  distance < 0.05 → return existing UUID.
      3. Gate 2 (parent):   distance < 0.30 among root topics → use as parent.
      4. Insert new row, return new UUID.

    Returns a list of UUID strings, one per input topic.
    """
    result_uuids: list[str] = []

    for topic_str in dynamic_topics:
        if not isinstance(topic_str, str) or not topic_str.strip():
            continue

        topic_str = topic_str.strip()
        vec = _embed(topic_str)
        vec_literal = str(vec)

        # Gate 1 — synonym match
        synonym_id = _find_synonym(db, vec_literal)
        if synonym_id is not None:
            logger.debug("Synonym match for '%s' → %s", topic_str, synonym_id)
            result_uuids.append(synonym_id)
            continue

        # Gate 2 — parent hierarchy
        parent_id = _find_parent(db, vec_literal)
        if parent_id is not None:
            logger.debug("Parent match for '%s' → parent %s", topic_str, parent_id)
        else:
            logger.debug("No parent found for '%s'; inserting as root", topic_str)

        # Insert new topic
        new_topic = Topic(
            id=uuid.uuid4(),
            name=topic_str,
            embedding=vec,
            parent_id=uuid.UUID(parent_id) if parent_id else None,
        )

        try:
            db.add(new_topic)
            db.commit()
            db.refresh(new_topic)
            new_id = str(new_topic.id)
            logger.info("Inserted new topic '%s' → %s", topic_str, new_id)
            result_uuids.append(new_id)
        except IntegrityError:
            # Unique-name collision: another request inserted first
            db.rollback()
            existing = db.query(Topic).filter(Topic.name == topic_str).first()
            if existing:
                logger.info("Duplicate name '%s' resolved → %s", topic_str, existing.id)
                result_uuids.append(str(existing.id))
            else:
                logger.warning("IntegrityError for '%s' but row not found after rollback", topic_str)

    return result_uuids
