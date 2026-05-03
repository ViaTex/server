from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobApplicationCreateRequest(BaseModel):
    expected_salary: Optional[Decimal] = Field(None, ge=0)
    cover_letter: Optional[str] = None


class JobApplicationUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, min_length=1, max_length=50)
    offer_letter: Optional[str] = None


class JobApplicationResponse(BaseModel):
    id: UUID
    job_id: UUID
    student_id: UUID
    corporate_id: Optional[UUID] = None
    college_id: Optional[UUID] = None
    status: str
    expected_salary: Optional[Decimal] = None
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = None
    offer_letter: Optional[str] = None
    offer_letter_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_phone: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    salary_currency: Optional[str] = None

    class Config:
        from_attributes = True
