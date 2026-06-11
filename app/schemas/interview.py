from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.interview import InterviewOutcome, InterviewStatus, InterviewType


class InterviewCreate(BaseModel):
    job_application_id: str
    student_id: str
    proposed_slots: list[datetime] = Field(default_factory=list)
    duration_minutes: int = Field(45, ge=15, le=180)
    meeting_link: Optional[str] = Field(None, max_length=1000)
    interview_type: InterviewType = InterviewType.TECHNICAL


class InterviewConfirm(BaseModel):
    scheduled_at: datetime
    meeting_link: Optional[str] = Field(None, max_length=1000)


class InterviewComplete(BaseModel):
    interviewer_notes: Optional[str] = None
    outcome: InterviewOutcome


class VerifiedSkillResponse(BaseModel):
    skill_name: str
    total_score: Optional[int] = None
    verdict: Optional[str] = None
    mentor_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    project_title: Optional[str] = None


class InterviewResponse(BaseModel):
    id: str
    job_application_id: str
    corporate_id: str
    student_id: str
    proposed_slots: list[datetime] = Field(default_factory=list)
    scheduled_at: Optional[datetime] = None
    duration_minutes: int
    meeting_link: Optional[str] = None
    interview_type: InterviewType
    status: InterviewStatus
    interviewer_notes: Optional[str] = None
    outcome: Optional[InterviewOutcome] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # enriched fields
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    company_website: Optional[str] = None
    company_description: Optional[str] = None
    company_address: Optional[str] = None
    job_description: Optional[str] = None
    job_requirements: Optional[str] = None
    job_responsibilities: Optional[str] = None
    contact_person: Optional[str] = None
    contact_designation: Optional[str] = None
    verified_skills: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
