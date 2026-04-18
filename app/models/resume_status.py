from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class ResumeStatus(Base):
    __tablename__ = "resume_status"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # One resume status per student
    )
    
    # Basic Resume Information
    has_resume = Column(Boolean, default=False, nullable=False)
    resume_uploaded = Column(Boolean, default=False, nullable=False)
    resume_url = Column(String(1000), nullable=True)
    can_upload = Column(Boolean, default=True, nullable=False)
    
    # ATS Score Information
    ats_score = Column(Integer, nullable=True)
    overall_assessment = Column(String(2000), nullable=True)
    formatting_score = Column(Integer, nullable=True)
    content_score = Column(Integer, nullable=True)
    keyword_score = Column(Integer, nullable=True)
    
    # Analysis Data (JSON)
    strengths = Column(JSONB, nullable=True)  # Array of strings
    weaknesses = Column(JSONB, nullable=True)  # Array of strings
    recommendations = Column(JSONB, nullable=True)  # Array of strings
    
    keyword_analysis = Column(JSONB, nullable=True)  # {"found_keywords": [...], "missing_keywords": [...]}
    sections_analysis = Column(JSONB, nullable=True)  # {"contact_information": "...", "professional_summary": "...", ...}
    extracted_skills = Column(JSONB, nullable=True)  # {"technical_skills": [...], "soft_skills": [...], ...}
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    ats_calculated_at = Column(DateTime(timezone=True), nullable=True)
