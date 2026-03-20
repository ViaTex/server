from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.embeddings.generator import generate_embedding
from app.models.exam_response import ExamResponse


def create_exam_response(
    db: Session,
    *,
    session_id: UUID,
    section_type: str,
    question_text: str,
    user_response: str,
    transcript: str | None = None,
) -> ExamResponse:
    response = ExamResponse(
        session_id=session_id,
        section_type=section_type,
        question_text=question_text,
        question_embedding=generate_embedding(question_text) if question_text else None,
        user_response=user_response,
        response_embedding=generate_embedding(user_response) if user_response else None,
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
    response.user_response = user_response
    response.response_embedding = generate_embedding(user_response) if user_response else None
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
