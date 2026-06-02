from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.embeddings.generator import generate_embedding
from app.models.exam_response import ExamResponse


def _collect_text_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float, bool)):
        return [str(value)]
    if isinstance(value, list):
        collected: list[str] = []
        for item in value:
            collected.extend(_collect_text_values(item))
        return collected
    if isinstance(value, dict):
        collected: list[str] = []
        for key, item in value.items():
            if key == "video_url":
                continue
            collected.extend(_collect_text_values(item))
        return collected
    return [str(value)]


def extract_text_for_embedding(payload: str) -> str:
    try:
        data = json.loads(payload)
    except Exception:
        return payload

    if not isinstance(data, dict):
        return payload

    text_parts: list[str] = []
    for key in (
        "prompt_text",
        "text_answer",
        "mcqs",
        "long_questions",
        "mcq_answers",
        "long_answers",
    ):
        text_parts.extend(_collect_text_values(data.get(key)))

    return "\n".join(part for part in text_parts if part)


def create_exam_response(
    db: Session,
    *,
    session_id: UUID,
    section_type: str,
    question_text: str,
    user_response: str,
    transcript: str | None = None,
) -> ExamResponse:
    question_embedding_text = extract_text_for_embedding(question_text) if question_text else ""
    response_embedding_text = extract_text_for_embedding(user_response) if user_response else ""
    response = ExamResponse(
        session_id=session_id,
        section_type=section_type,
        question_text=question_text,
        question_embedding=generate_embedding(question_embedding_text) if question_embedding_text else None,
        user_response=user_response,
        response_embedding=generate_embedding(response_embedding_text) if response_embedding_text else None,
        transcript=transcript,
    )
    db.add(response)
    db.commit()
    db.refresh(response)
    return response


def update_response_answer(
    db: Session,
    *,
    response: ExamResponse,
    user_response: str,
) -> ExamResponse:
    response_embedding_text = extract_text_for_embedding(user_response)
    response.user_response = user_response
    response_embedding_text = extract_text_for_embedding(user_response) if user_response else ""
    response.response_embedding = generate_embedding(response_embedding_text) if response_embedding_text else None
    db.add(response)
    db.commit()
    db.refresh(response)
    return response


def update_response_ai_analysis(
    db: Session,
    *,
    response: ExamResponse,
    transcript: str | None,
    ai_analysis: dict[str, Any],
) -> ExamResponse:
    if transcript is not None:
        response.transcript = transcript
    response.ai_score = ai_analysis.get("score")
    response.ai_feedback = ai_analysis.get("feedback")
    db.add(response)
    db.commit()
    db.refresh(response)
    return response
