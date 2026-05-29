from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.exam_session import ExamSession
from app.models.exam_response import ExamResponse


def _failed_attempts(db: Session, student_id: UUID, exam_level: str) -> int:
    return (
        db.query(ExamSession)
        .filter(
            ExamSession.student_id == student_id,
            ExamSession.exam_level == exam_level,
            ExamSession.attempt_number > 0,
            ExamSession.is_passed.is_(False),
        )
        .count()
    )


def create_exam_session(
    db: Session,
    *,
    student_id: UUID,
    exam_level: str,
) -> ExamSession:
    attempts = _failed_attempts(db, student_id, exam_level)
    if attempts >= 3:
        raise ValueError("Maximum attempts reached")

    exam_session = ExamSession(
        student_id=student_id,
        attempt_number=attempts + 1,
        exam_level=exam_level,
        total_des_score=None,
        growth_rate=None,
        is_passed=False,
        performance_snapshot=None,
        current_step="SECTION_A",
        completed_at=None,
    )
    db.add(exam_session)
    db.commit()
    db.refresh(exam_session)
    return exam_session


def get_exam_session(db: Session, *, session_id: UUID, student_id: UUID) -> ExamSession:
    session = (
        db.query(ExamSession)
        .filter(ExamSession.id == session_id, ExamSession.student_id == student_id)
        .first()
    )
    if not session:
        raise ValueError("Exam session not found")
    return session


def set_current_step(db: Session, *, session: ExamSession, next_step: str) -> ExamSession:
    session.current_step = next_step
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def mark_abandoned(db: Session, *, session: ExamSession) -> ExamSession:
    session.current_step = "ABANDONED"
    session.total_des_score = 0
    session.is_passed = False
    session.completed_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def finalize_exam(
    db: Session,
    *,
    session: ExamSession,
    total_des_score: float,
    growth_rate: float | None,
    performance_snapshot: dict,
    is_passed: bool,
) -> ExamSession:
    session.total_des_score = total_des_score
    session.growth_rate = growth_rate
    session.performance_snapshot = performance_snapshot
    session.is_passed = is_passed
    if is_passed:
        session.attempt_number = 0
    session.current_step = "FINALIZED"
    session.completed_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_exam_scores_from_responses(db: Session, *, session: ExamSession) -> ExamSession:
    responses = (
        db.query(ExamResponse)
        .filter(ExamResponse.session_id == session.id)
        .all()
    )

    weights = {
        "A_INTRO": 0.10,
        "B_FUNDAMENTALS": 0.20,
        "C_LOGIC": 0.30,
        "D_DEBUG": 0.40,
    }
    score_map = {key: 0.0 for key in weights}
    hints_map = {key: 0 for key in weights}

    for response in responses:
        if response.section_type in score_map:
            score_map[response.section_type] = float(response.ai_score or 0.0)
            hints_map[response.section_type] = int(response.hints_used or 0)

    total = sum(score_map[key] * weights[key] for key in weights)
    session.total_des_score = round(total, 2)
    session.performance_snapshot = {
        "scores": score_map,
        "hints_used": hints_map,
    }

    db.add(session)
    db.commit()
    db.refresh(session)
    return session
