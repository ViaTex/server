from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.core.database import Base


class JobType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"


class WorkMode(str, enum.Enum):
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"


class JobStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"
    DRAFT = "draft"


job_type_enum = Enum(JobType, name="jobtype", values_callable=lambda enum_cls: [item.value for item in enum_cls])
work_mode_enum = Enum(WorkMode, name="workmode", values_callable=lambda enum_cls: [item.value for item in enum_cls])
job_status_enum = Enum(JobStatus, name="jobstatus", values_callable=lambda enum_cls: [item.value for item in enum_cls])


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    job_type = Column(job_type_enum, nullable=False)
    status = Column(job_status_enum, nullable=False, default=JobStatus.ACTIVE)
    location = Column(String(255), nullable=False)
    remote_work = Column(Boolean, nullable=False, default=False)
    travel_required = Column(Boolean, nullable=False, default=False)
    mode_of_work = Column(work_mode_enum, nullable=True)

    salary_min = Column(Numeric(12, 2), nullable=True)
    salary_max = Column(Numeric(12, 2), nullable=True)
    salary_currency = Column(String(3), nullable=False, default="INR")
    ctc_with_probation = Column(String(255), nullable=True)
    ctc_after_probation = Column(String(255), nullable=True)

    experience_min = Column(Integer, nullable=True)
    experience_max = Column(Integer, nullable=True)
    education_level = Column(JSONB, nullable=True)
    education_degree = Column(JSONB, nullable=True)
    education_branch = Column(JSONB, nullable=True)
    skills_required = Column(JSONB, nullable=True)
    certifications_required = Column(Text, nullable=True)

    application_deadline = Column(DateTime(timezone=True), nullable=True)
    max_applications = Column(Integer, nullable=False, default=100)
    current_applications = Column(Integer, nullable=False, default=0)
    industry = Column(String(255), nullable=True)
    joining_location = Column(String(255), nullable=True)
    selection_process = Column(Text, nullable=True)
    campus_drive_date = Column(DateTime(timezone=True), nullable=True)
    service_agreement_details = Column(Text, nullable=True)
    number_of_openings = Column(Integer, nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    perks_and_benefits = Column(Text, nullable=True)
    eligibility_criteria = Column(Text, nullable=True)

    company_name = Column(String(255), nullable=True)
    company_logo = Column(Text, nullable=True)
    company_website = Column(String(500), nullable=True)
    company_address = Column(String(500), nullable=True)
    company_size = Column(String(50), nullable=True)
    company_type = Column(String(100), nullable=True)
    company_founded = Column(Integer, nullable=True)
    company_description = Column(Text, nullable=True)
    contact_person = Column(String(255), nullable=True)
    contact_designation = Column(String(255), nullable=True)

    min_des_score = Column(Numeric(5, 2), nullable=True)
    max_des_score = Column(Numeric(5, 2), nullable=True)
    ongoing_project_title = Column(String(255), nullable=True)
    ongoing_project_description = Column(Text, nullable=True)

    corporate_id = Column(UUID(as_uuid=True), ForeignKey("corporates.id"), nullable=True, index=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=True, index=True)

    views_count = Column(Integer, nullable=False, default=0)
    applications_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    tenant_id = Column(String(50), nullable=False, default="default")
    is_public = Column(Boolean, nullable=False, default=False)
    public_link_token = Column(String(255), nullable=True, unique=True)

    @property
    def is_active(self) -> bool:
        if self.status != JobStatus.ACTIVE:
            return False
        return True

    @property
    def can_apply(self) -> bool:
        return self.is_active and self.current_applications < self.max_applications
