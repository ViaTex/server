from __future__ import annotations

import json
import re
from typing import Iterable

from app.core.redis import get_redis_client


GLOBAL_TOPICS_KEY = "global_topics"


def _sanitize_topic(topic: str) -> str | None:
    if not isinstance(topic, str):
        return None

    cleaned = topic.strip()
    if not cleaned:
        return None

    cleaned = re.sub(r"[_-]+", " ", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9 ]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None

    words = cleaned.split(" ")[:3]
    cleaned = " ".join(words).title().strip()
    return cleaned or None


def get_global_topics() -> list[str]:
    redis_client = get_redis_client()
    cached = redis_client.get(GLOBAL_TOPICS_KEY)
    if not cached:
        return []

    try:
        payload = json.loads(cached)
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, list):
        return []

    return [item for item in payload if isinstance(item, str) and item.strip()]


def update_global_topics(new_topics: Iterable[str]) -> list[str]:
    redis_client = get_redis_client()
    existing = get_global_topics()
    existing_set = {topic.lower() for topic in existing}

    for topic in new_topics or []:
        sanitized = _sanitize_topic(topic)
        if not sanitized:
            continue
        if sanitized.lower() in existing_set:
            continue
        existing.append(sanitized)
        existing_set.add(sanitized.lower())

    redis_client.set(GLOBAL_TOPICS_KEY, json.dumps(existing))
    return existing
