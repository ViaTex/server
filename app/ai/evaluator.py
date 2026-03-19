from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings


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


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    if not raw_text:
        return None
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = raw_text[start : end + 1]
    try:
        return json.loads(snippet)
    except json.JSONDecodeError:
        return None


def analyze_transcript(transcript: str) -> dict[str, Any]:
    _ensure_groq_config()
    cleaned = (transcript or "").strip()
    if not cleaned:
        raise ValueError("Transcript is empty")

    system_prompt = (
        "You are an expert evaluator for student introduction videos. "
        "Assess the transcript for Linguistic Confidence and Communication Clarity. "
        "Return ONLY valid JSON with this schema: "
        "{\"score\": <number 1-10>, \"feedback\": {\"strengths\": [..], \"gaps\": [..]}}. "
        "Strengths and gaps must be concise phrases."
    )
    user_prompt = f"Transcript:\n{cleaned}"

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
        "temperature": 0.2,
        "max_tokens": 400,
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

    analysis = None
    if raw_text:
        try:
            analysis = json.loads(raw_text)
        except json.JSONDecodeError:
            analysis = _extract_json_object(raw_text)

    if not isinstance(analysis, dict):
        analysis = {
            "score": 5,
            "feedback": {
                "strengths": ["Basic clarity"],
                "gaps": ["Needs more detail"],
            },
        }

    score = analysis.get("score")
    try:
        score_value = float(score)
    except (TypeError, ValueError):
        score_value = 5.0

    score_value = max(1.0, min(10.0, score_value))
    feedback = analysis.get("feedback") if isinstance(analysis.get("feedback"), dict) else {}
    strengths = feedback.get("strengths") if isinstance(feedback.get("strengths"), list) else []
    gaps = feedback.get("gaps") if isinstance(feedback.get("gaps"), list) else []

    return {
        "score": round(score_value, 2),
        "feedback": {
            "strengths": strengths,
            "gaps": gaps,
        },
    }
