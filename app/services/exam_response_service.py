from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.embeddings.generator import generate_embedding
from app.models.exam_response import ExamResponse


def _collect_text(value: object, parts: list[str]) -> None:
    if value is None:
        return
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            parts.append(cleaned)
        return
    if isinstance(value, dict):
        for item in value.values():
            _collect_text(item, parts)
        return
    if isinstance(value, list):
        for item in value:
            _collect_text(item, parts)


def extract_text_for_embedding(payload: str) -> str:
    if not payload:
        return ""
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return payload

    if not isinstance(parsed, dict):
        return payload

    parts: list[str] = []
    _collect_text(parsed.get("prompt_text"), parts)
    _collect_text(parsed.get("mcqs"), parts)
    _collect_text(parsed.get("long_questions"), parts)
    _collect_text(parsed.get("text_answer"), parts)
    _collect_text(parsed.get("mcq_answers"), parts)
    _collect_text(parsed.get("long_answers"), parts)

    return "\n".join(parts).strip()


def create_exam_response(
    db: Session,
    *,
    session_id: UUID,
    section_type: str,
    question_text: str,
    user_response: str,
    transcript: str | None = None,
) -> ExamResponse:
    question_embedding_text = extract_text_for_embedding(question_text)
    response_embedding_text = extract_text_for_embedding(user_response)
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
    response.response_embedding = (
        generate_embedding(response_embedding_text) if response_embedding_text else None
    )
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
