from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import SkillEvaluationStatus, SkillEvaluationVerdict


class MentorProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    current_role: Optional[str] = Field(None, max_length=255)
    expertise_areas: Optional[list[str]] = None
    experience_years: Optional[int] = Field(None, ge=0, le=80)
    motivation: Optional[str] = None


class MentorProfileResponse(BaseModel):
    id: str
    user_id: str
    email: EmailStr
    name: str
    phone: Optional[str] = None
    current_role: Optional[str] = None
    expertise_areas: list[str] = Field(default_factory=list)
    experience_years: Optional[int] = None
    motivation: Optional[str] = None
    average_rating: float = 0.0

    class Config:
        from_attributes = True


class SkillEvaluationCreate(BaseModel):
    student_id: str
    project_id: Optional[str] = None
    status: SkillEvaluationStatus = SkillEvaluationStatus.SUBMITTED
    proposed_slots: list[datetime] = Field(default_factory=list)
    confirmed_slot: Optional[datetime] = None
    viva_meeting_link: Optional[str] = Field(None, max_length=1000)


class SkillEvaluationScheduleUpdate(BaseModel):
    status: Optional[SkillEvaluationStatus] = None
    proposed_slots: Optional[list[datetime]] = None
    confirmed_slot: Optional[datetime] = None
    viva_meeting_link: Optional[str] = Field(None, max_length=1000)


class SkillEvaluationScoringUpdate(BaseModel):
    status: Optional[SkillEvaluationStatus] = None
    score_technical: Optional[int] = Field(None, ge=0, le=40)
    score_practical: Optional[int] = Field(None, ge=0, le=30)
    score_communication: Optional[int] = Field(None, ge=0, le=20)
    score_originality: Optional[int] = Field(None, ge=0, le=10)
    total_score: Optional[int] = Field(None, ge=0, le=100)
    verdict: Optional[SkillEvaluationVerdict] = None
    feedback_strengths: Optional[str] = None
    feedback_improvements: Optional[str] = None


class SkillEvaluationStudentReviewUpdate(BaseModel):
    student_rating_of_mentor: Optional[int] = Field(None, ge=1, le=5)
    student_technical_issues: Optional[str] = None


class SkillEvaluationResponse(BaseModel):
    evaluation_id: str
    mentor_id: str
    student_id: str
    project_id: Optional[str] = None
    status: SkillEvaluationStatus
    proposed_slots: list[datetime] = Field(default_factory=list)
    confirmed_slot: Optional[datetime] = None
    viva_meeting_link: Optional[str] = None
    score_technical: Optional[int] = None
    score_practical: Optional[int] = None
    score_communication: Optional[int] = None
    score_originality: Optional[int] = None
    total_score: Optional[int] = None
    verdict: Optional[SkillEvaluationVerdict] = None
    feedback_strengths: Optional[str] = None
    feedback_improvements: Optional[str] = None
    student_rating_of_mentor: Optional[int] = None
    student_technical_issues: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
