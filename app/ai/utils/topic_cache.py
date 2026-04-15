from __future__ import annotations

import json
import re
from typing import Iterable

from app.core.redis import get_redis_client


TOPIC_CACHE_KEY = "global_topics"


def _normalize_topic(topic: str) -> str:
    if not topic:
        return ""
    cleaned = re.sub(r"[^A-Za-z\s]", " ", topic)
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        return ""
    words = cleaned.split()[:3]
    normalized = " ".join(word.lower() for word in words).title()
    return normalized


def sanitize_topics(topics: Iterable[str]) -> list[str]:
    result: list[str] = []
    for item in topics:
        if not isinstance(item, str):
            continue
        normalized = _normalize_topic(item)
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def get_global_topics(redis_client=None) -> list[str]:
    client = redis_client or get_redis_client()
    cached = client.get(TOPIC_CACHE_KEY)
    if not cached:
        return []
    try:
        payload = json.loads(cached)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return sanitize_topics(payload)


def update_global_topics(topics: Iterable[str], redis_client=None) -> list[str]:
    client = redis_client or get_redis_client()
    existing = get_global_topics(client)
    normalized = sanitize_topics(topics)
    merged = existing[:]
    for topic in normalized:
        if topic not in merged:
            merged.append(topic)
    client.set(TOPIC_CACHE_KEY, json.dumps(merged))
    return merged
