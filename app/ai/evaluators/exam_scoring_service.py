from __future__ import annotations

import json

from app.ai.evaluator import generate_chat_completion


def score_text_response(*, section_type: str, question_text: str, user_response: str) -> dict:
    system_prompt = (
        "You are an exam evaluator. Return ONLY valid JSON with schema: "
        "{\"score\": <number 1-10>, \"feedback\": {\"strengths\": [..], \"gaps\": [..]}}."
    )
    user_prompt = (
        f"Section type: {section_type}.\n"
        f"Question: {question_text}\n"
        f"Student answer: {user_response}\n"
        "Score the response fairly with concise strengths and gaps."
    )

    raw = generate_chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=300,
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}

    score = data.get("score")
    try:
        score_value = float(score)
    except (TypeError, ValueError):
        score_value = 5.0

    score_value = max(1.0, min(10.0, score_value))
    feedback = data.get("feedback") if isinstance(data.get("feedback"), dict) else {}
    strengths = feedback.get("strengths") if isinstance(feedback.get("strengths"), list) else []
    gaps = feedback.get("gaps") if isinstance(feedback.get("gaps"), list) else []

    return {
        "score": round(score_value, 2),
        "feedback": {
            "strengths": strengths,
            "gaps": gaps,
        },
    }
