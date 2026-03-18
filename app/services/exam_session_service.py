from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.exam_session import ExamSession


def _exam_json_template() -> dict[str, Any]:
    return {
        "metadata": {
            "exam_domain": None,
            "difficulty_level": None,
        },
        "assistance_metrics": {
            "total_hints_count": 0,
            "hint_history": [],
        },
        "sections": {
            "section_a_intro": {
                "video_url": None,
                "transcript": None,
                "ai_analysis": {
                    "feedback": None,
                    "score": None,
                },
                "mentor_analysis": {
                    "feedback": None,
                    "score": None,
                },
                "final_section_score": None,
            }
        },
    }


def merge_exam_section(
    current_exam_json: dict[str, Any] | None,
    section_key: str,
    section_payload: dict[str, Any],
) -> dict[str, Any]:
    merged = _exam_json_template()

    if isinstance(current_exam_json, dict):
        merged = deepcopy(current_exam_json)

    merged.setdefault("metadata", {"exam_domain": None, "difficulty_level": None})
    merged.setdefault("assistance_metrics", {"total_hints_count": 0, "hint_history": []})
    merged.setdefault("sections", {})

    sections = merged.get("sections")
    if not isinstance(sections, dict):
        sections = {}
        merged["sections"] = sections

    existing = sections.get(section_key)
    if isinstance(existing, dict):
        next_section = deepcopy(existing)
        next_section.update(section_payload)
        sections[section_key] = next_section
    else:
        sections[section_key] = section_payload

    return merged


def _next_attempt_number(db: Session, student_id: UUID, exam_level: str) -> int:
    current_max = (
        db.query(func.max(ExamSession.attempt_number))
        .filter(
            ExamSession.student_id == student_id,
            ExamSession.exam_level == exam_level,
        )
        .scalar()
    )
    return int(current_max or 0) + 1


def create_intro_exam_session(
    db: Session,
    *,
    student_id: UUID,
    exam_level: str,
    video_url: str,
) -> ExamSession:
    section_intro_payload = {
        "video_url": video_url,
        "transcript": None,
        "ai_analysis": {
            "feedback": None,
            "score": None,
        },
        "mentor_analysis": {
            "feedback": None,
            "score": None,
        },
        "final_section_score": None,
    }

    exam_json = merge_exam_section(None, "section_a_intro", section_intro_payload)

    exam_session = ExamSession(
        student_id=student_id,
        attempt_number=_next_attempt_number(db, student_id, exam_level),
        exam_level=exam_level,
        exam_json=exam_json,
        growth_rate=None,
        is_passed=False,
        completed_at=None,
    )

    db.add(exam_session)
    db.commit()
    db.refresh(exam_session)
    return exam_session
