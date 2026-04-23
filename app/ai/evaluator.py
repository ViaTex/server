from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.ai.evaluate import evaluate_section_a_transcript


GROQ_API_BASE = "https://api.groq.com/openai/v1"


def _ensure_groq_config() -> None:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")
    if not settings.GROQ_TRANSCRIPTION_MODEL:
        raise RuntimeError("GROQ_TRANSCRIPTION_MODEL is not configured")
    if not settings.GROQ_ANALYSIS_MODEL:
        raise RuntimeError("GROQ_ANALYSIS_MODEL is not configured")


def download_media(url: str, *, timeout_seconds: int = 120) -> bytes:
    if not url:
        raise ValueError("Missing media URL")

    with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def transcribe_media(media_bytes: bytes, *, filename: str = "intro.mp4") -> str:
    _ensure_groq_config()
    if not media_bytes:
        raise ValueError("Empty media content")

    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
    files = {
        "file": (filename, media_bytes, "application/octet-stream"),
    }
    data = {"model": settings.GROQ_TRANSCRIPTION_MODEL}

    with httpx.Client(timeout=180) as client:
        response = client.post(
            f"{GROQ_API_BASE}/audio/transcriptions",
            headers=headers,
            files=files,
            data=data,
        )
        response.raise_for_status()
        payload = response.json()

    transcript = payload.get("text")
    if not transcript:
        raise RuntimeError("Transcription response missing text")
    return str(transcript).strip()


def analyze_transcript(transcript: str, *, topics: list[str]) -> dict[str, Any]:
    _ensure_groq_config()
    return evaluate_section_a_transcript(transcript, topics)


def generate_chat_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.4,
    max_tokens: int = 300,
) -> str:
    _ensure_groq_config()

    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GROQ_ANALYSIS_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    with httpx.Client(timeout=120) as client:
        response = client.post(
            f"{GROQ_API_BASE}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        result = response.json()

    raw_text = ""
    try:
        raw_text = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raw_text = ""

    return str(raw_text or "").strip()
