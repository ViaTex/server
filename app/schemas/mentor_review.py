from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.exams import MentorFeedback


class ExamReviewAssignmentItem(BaseModel):
    session_id: str
    student_id: str
    mentor_id: str | None
    status: str
    assigned_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime | None


class ExamReviewResponsePayload(BaseModel):
    response_id: str
    section_type: str
    question_text: Any
    user_response: Any
    video_url: str | None
    transcript: str | None
    ai_score: float | None
    ai_feedback: Any
    mentor_score: float | None
    mentor_feedback: Any


class ExamReviewStudentPayload(BaseModel):
    student_id: str
    name: str
    technical_skills: str | None
    resume_url: str | None


class ExamReviewAssignmentDetail(BaseModel):
    session_id: str
    current_step: str
    exam_level: str
    student: ExamReviewStudentPayload
    section_a: ExamReviewResponsePayload
    section_d: ExamReviewResponsePayload


class MentorSectionScore(BaseModel):
    score: float = Field(..., ge=0, le=10)
    feedback: MentorFeedback
    topic_scores: dict[str, float] | None = None


class MentorExamReviewScore(BaseModel):
    section_a: MentorSectionScore
    section_d: MentorSectionScore
