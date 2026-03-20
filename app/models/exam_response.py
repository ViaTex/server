from __future__ import annotations

import uuid

from sqlalchemy import Column, ForeignKey, Integer, Numeric, Text, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class ExamResponse(Base):
    __tablename__ = "exam_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exam_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_type = Column(String(32), nullable=False)
    question_text = Column(Text, nullable=False)
    question_embedding = Column(Vector(384), nullable=True)
    user_response = Column(Text, nullable=False)
    response_embedding = Column(Vector(384), nullable=True)
    transcript = Column(Text, nullable=True)
    ai_score = Column(Numeric(6, 2), nullable=True)
    ai_feedback = Column(JSONB, nullable=True)
    mentor_score = Column(Numeric(6, 2), nullable=True)
    mentor_feedback = Column(JSONB, nullable=True)
    hints_used = Column(Integer, nullable=False, default=0)

    session = relationship("ExamSession", back_populates="responses")
