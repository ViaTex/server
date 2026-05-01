from __future__ import annotations

import json
from typing import Any


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


def _coerce_score(value: object, default: float = 5.0) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    return max(1.0, min(10.0, score))


def build_section_a_prompt(topics: list[str]) -> str:
    cleaned_topics = [topic for topic in topics if isinstance(topic, str) and topic.strip()]
    if not cleaned_topics:
        raise ValueError("Topics must be provided for evaluation")

    topic_schema = ", ".join([f"\\\"{topic}\\\": <1-10>" for topic in cleaned_topics])

    return (
        "You are an interview evaluator. You must ONLY score these topics: "
        f"{cleaned_topics}. You are strictly forbidden from creating or extracting any new topics. "
        "Return ONLY JSON matching this schema: "
        "{\"score\": <number 1-10>, "
        f"\"topic_scores\": {{{topic_schema}}}, "
        "\"strengths\": [..], \"areas_for_improvement\": [..], "
        "\"behavioral_analysis\": \"...\"}."
    )


def parse_section_a_analysis(raw_text: str, topics: list[str]) -> dict[str, Any]:
    payload = None
    if raw_text:
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            payload = _extract_json_object(raw_text)

    if not isinstance(payload, dict):
        payload = {}

    feedback_payload = payload.get("feedback") if isinstance(payload.get("feedback"), dict) else payload

    topic_scores = (
        feedback_payload.get("topic_scores")
        if isinstance(feedback_payload.get("topic_scores"), dict)
        else {}
    )
    normalized_scores = {
        topic: _coerce_score(topic_scores.get(topic))
        for topic in topics
        if isinstance(topic, str) and topic.strip()
    }

    strengths = (
        feedback_payload.get("strengths")
        if isinstance(feedback_payload.get("strengths"), list)
        else []
    )
    areas = (
        feedback_payload.get("areas_for_improvement")
        if isinstance(feedback_payload.get("areas_for_improvement"), list)
        else []
    )

    strengths = [item for item in strengths if isinstance(item, str) and item.strip()]
    areas = [item for item in areas if isinstance(item, str) and item.strip()]

    if len(strengths) < 2:
        strengths = (strengths + ["Clear intent", "Relevant experience"])[:2]
    if len(areas) < 2:
        areas = (areas + ["Add more structure", "Reduce filler words"])[:2]

    strengths = strengths[:3]
    areas = areas[:3]

    behavioral_analysis = feedback_payload.get("behavioral_analysis")
    if not isinstance(behavioral_analysis, str) or not behavioral_analysis.strip():
        behavioral_analysis = "The response shows mixed clarity and needs more structured delivery."

    default_score = 5.0
    if normalized_scores:
        default_score = sum(normalized_scores.values()) / len(normalized_scores)

    score_value = _coerce_score(payload.get("score"), default=default_score)

    return {
        "score": round(score_value, 2),
        "feedback": {
            "topic_scores": normalized_scores,
            "strengths": strengths,
            "areas_for_improvement": areas,
            "behavioral_analysis": behavioral_analysis,
        },
    }


def evaluate_section_a_transcript(
    transcript: str,
    topics: list[str],
    *,
    temperature: float = 0.2,
    max_tokens: int = 320,
) -> dict[str, Any]:
    cleaned = (transcript or "").strip()
    if not cleaned:
        raise ValueError("Transcript is empty")

    system_prompt = build_section_a_prompt(topics)
    user_prompt = f"Transcript:\n{cleaned}"

    from app.ai.evaluator import generate_chat_completion

    raw_text = generate_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return parse_section_a_analysis(raw_text, topics)
