from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number = Column(Integer, nullable=False)
    exam_level = Column(String(100), nullable=False)
    total_des_score = Column(Numeric(6, 2), nullable=True)
    growth_rate = Column(Numeric(6, 2), nullable=True)
    is_passed = Column(Boolean, nullable=False, default=False)
    performance_snapshot = Column(JSONB, nullable=True)
    current_step = Column(String(32), nullable=False, default="SECTION_A")
    completed_at = Column(DateTime(timezone=True), nullable=True)

    student = relationship("Student", back_populates="exam_sessions")
    responses = relationship("ExamResponse", back_populates="session", cascade="all, delete-orphan")