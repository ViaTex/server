from __future__ import annotations

from datetime import datetime, timezone
import random
import re

from sqlalchemy.orm import Session

from app.models.exam_review_assignment import ExamReviewAssignment
from app.models.exam_session import ExamSession
from app.models.user import Mentor, Student


_SPLIT_PATTERN = re.compile(r"[\n,;/|]+")
_ALLOWED_CHARS_PATTERN = re.compile(r"[^a-z0-9+.#\- ]+")


def _normalize_chunk(raw: str) -> str:
    cleaned = raw.strip().lower()
    if not cleaned:
        return ""
    cleaned = _ALLOWED_CHARS_PATTERN.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _collect_keywords(text: str | None) -> set[str]:
    if not text:
        return set()

    keywords: set[str] = set()
    for chunk in _SPLIT_PATTERN.split(text):
        normalized = _normalize_chunk(chunk)
        if not normalized:
            continue
        keywords.add(normalized)
        if " " in normalized:
            for token in normalized.split(" "):
                if token:
                    keywords.add(token)
    return keywords


def _collect_expertise_keywords(expertise_areas: list[str] | None) -> set[str]:
    if not expertise_areas:
        return set()

    keywords: set[str] = set()
    for item in expertise_areas:
        if not isinstance(item, str):
            continue
        normalized = _normalize_chunk(item)
        if not normalized:
            continue
        keywords.add(normalized)
        if " " in normalized:
            for token in normalized.split(" "):
                if token:
                    keywords.add(token)
    return keywords


def _mentor_matches(student_keywords: set[str], mentor_keywords: set[str]) -> bool:
    if not student_keywords or not mentor_keywords:
        return False
    return mentor_keywords.issubset(student_keywords)


def find_matching_mentors(db: Session, *, student: Student) -> list[Mentor]:
    student_keywords = _collect_keywords(student.technical_skills)
    if not student_keywords:
        return []

    mentors = db.query(Mentor).all()
    matches: list[Mentor] = []
    for mentor in mentors:
        mentor_keywords = _collect_expertise_keywords(mentor.expertise_areas or [])
        if _mentor_matches(student_keywords, mentor_keywords):
            matches.append(mentor)
    return matches


def get_or_create_assignment(
    db: Session,
    *,
    session: ExamSession,
) -> ExamReviewAssignment:
    assignment = (
        db.query(ExamReviewAssignment)
        .filter(ExamReviewAssignment.session_id == session.id)
        .first()
    )
    if assignment:
        return assignment

    assignment = ExamReviewAssignment(
        session_id=session.id,
        status="queued",
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def assign_mentor_if_possible(
    db: Session,
    *,
    session: ExamSession,
    student: Student,
) -> ExamReviewAssignment:
    assignment = get_or_create_assignment(db, session=session)
    if assignment.mentor_id:
        return assignment

    matches = find_matching_mentors(db, student=student)
    if not matches:
        return assignment

    mentor = random.choice(matches)
    assignment.mentor_id = mentor.id
    assignment.status = "assigned"
    assignment.assigned_at = datetime.now(timezone.utc)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment
