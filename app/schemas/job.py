from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


JobType = Literal["full_time", "part_time", "contract", "internship", "freelance"]
WorkMode = Literal["onsite", "remote", "hybrid"]


class JobCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=10)
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    job_type: JobType
    location: str = Field(..., max_length=255)
    remote_work: bool = False
    travel_required: bool = False
    mode_of_work: Optional[WorkMode] = None
    salary_min: Optional[Decimal] = Field(None, ge=0)
    salary_max: Optional[Decimal] = Field(None, ge=0)
    salary_currency: str = Field("INR", min_length=3, max_length=3)
    ctc_with_probation: Optional[str] = None
    ctc_after_probation: Optional[str] = None
    experience_min: Optional[int] = Field(None, ge=0)
    experience_max: Optional[int] = Field(None, ge=0)
    education_level: Optional[List[str]] = None
    education_degree: Optional[List[str]] = None
    education_branch: Optional[List[str]] = None
    skills_required: Optional[List[str]] = None
    certifications_required: Optional[str] = None
    application_deadline: Optional[datetime] = None
    max_applications: int = Field(100, ge=1, le=1000)
    industry: Optional[str] = Field(None, max_length=255)
    selection_process: Optional[str] = None
    campus_drive_date: Optional[datetime] = None
    service_agreement_details: Optional[str] = None
    number_of_openings: Optional[int] = Field(None, ge=1, description="Number of job openings")
    expiration_date: Optional[datetime] = None
    perks_and_benefits: Optional[str] = None
    eligibility_criteria: Optional[str] = None

    company_name: Optional[str] = Field(None, max_length=255, description="Company name for university-created jobs")
    company_logo: Optional[str] = Field(None, description="Company logo URL")
    company_website: Optional[str] = Field(None, max_length=500, description="Company website URL")
    company_address: Optional[str] = Field(None, max_length=500, description="Company address")
    company_size: Optional[str] = Field(None, max_length=50, description="Company size (e.g., 1-10, 11-50)")
    company_type: Optional[str] = Field(None, max_length=100, description="Company type (e.g., Startup, Enterprise)")
    company_founded: Optional[int] = Field(None, ge=1900, le=2100, description="Company founded year")
    company_description: Optional[str] = Field(None, description="About the company")
    contact_person: Optional[str] = Field(None, max_length=255, description="Contact person name")
    contact_designation: Optional[str] = Field(None, max_length=255, description="Contact person designation")

    min_des_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Minimum desirability score")
    max_des_score: Optional[Decimal] = Field(None, ge=0, le=100, description="Maximum desirability score")
    ongoing_project_title: Optional[str] = Field(None, max_length=255, description="Title of the ongoing project")
    ongoing_project_description: Optional[str] = Field(None, description="Description of the ongoing project")

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValueError("salary_min must be less than or equal to salary_max")
        if self.experience_min is not None and self.experience_max is not None and self.experience_min > self.experience_max:
            raise ValueError("experience_min must be less than or equal to experience_max")
        if self.min_des_score is not None and self.max_des_score is not None and self.min_des_score > self.max_des_score:
            raise ValueError("min_des_score must be less than or equal to max_des_score")
        return self


class JobCreateSchema(JobCreateRequest):
    corporate_id: Optional[UUID] = None
    college_id: Optional[UUID] = None


class JobResponse(JobCreateSchema):
    id: UUID
    is_public: bool
    status: str
    views_count: int
    applications_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    published_at: Optional[datetime]
    can_apply: bool
    is_active: bool
    public_link_token: Optional[str]

    class Config:
        from_attributes = True

