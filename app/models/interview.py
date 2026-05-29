from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class InterviewType(str, enum.Enum):
    TECHNICAL = "technical"
    CULTURE_FIT = "culture_fit"
    HR = "hr"
    FINAL = "final"


class InterviewStatus(str, enum.Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InterviewOutcome(str, enum.Enum):
    PROCEED = "proceed"
    REJECT = "reject"
    HOLD = "hold"
    OFFER = "offer"


interview_type_enum = Enum(
    InterviewType,
    name="interviewtype",
    values_callable=lambda e: [i.value for i in e],
)
interview_status_enum = Enum(
    InterviewStatus,
    name="interviewstatus",
    values_callable=lambda e: [i.value for i in e],
)
interview_outcome_enum = Enum(
    InterviewOutcome,
    name="interviewoutcome",
    values_callable=lambda e: [i.value for i in e],
)


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    job_application_id = Column(
        UUID(as_uuid=True),
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    corporate_id = Column(
        UUID(as_uuid=True),
        ForeignKey("corporates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    proposed_slots = Column(JSONB, nullable=False, default=list)  # list of ISO datetime strings
    scheduled_at = Column(DateTime(timezone=True), nullable=True)  # confirmed slot
    duration_minutes = Column(Integer, nullable=False, default=45)
    meeting_link = Column(String(1000), nullable=True)
    interview_type = Column(interview_type_enum, nullable=False, default=InterviewType.TECHNICAL)
    status = Column(interview_status_enum, nullable=False, default=InterviewStatus.PROPOSED)

    interviewer_notes = Column(Text, nullable=True)
    outcome = Column(interview_outcome_enum, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    student = relationship("Student", backref="interviews")
    corporate = relationship("Corporate", backref="interviews")
