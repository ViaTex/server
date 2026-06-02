from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    SELECTED = "selected"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


application_status_enum = Enum(
    ApplicationStatus,
    name="applicationstatus",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint("job_id", "student_id", name="uq_job_applications_job_student"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    corporate_id = Column(UUID(as_uuid=True), ForeignKey("corporates.id"), nullable=True, index=True)
    college_id = Column(UUID(as_uuid=True), ForeignKey("colleges.id"), nullable=True, index=True)

    status = Column(application_status_enum, nullable=False, default=ApplicationStatus.APPLIED)
    expected_salary = Column(Numeric(12, 2), nullable=True)
    cover_letter = Column(Text, nullable=True)
    resume_url = Column(String(1000), nullable=False)
    offer_letter = Column(Text, nullable=True)
    offer_letter_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Placement tracking — set automatically when status → selected
    placed_at = Column(DateTime(timezone=True), nullable=True)
    placed_by_corporate_name = Column(String(255), nullable=True)
    placed_job_title = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
