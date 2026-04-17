"""Resume Status Service - Handle resume status record operations."""
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from app.models.resume_status import ResumeStatus


class ResumeStatusService:
    """Service for managing resume_status records."""

    @staticmethod
    def get_or_create(db: Session, student_id: UUID) -> ResumeStatus:
        """Get existing resume_status or create a new one."""
        status = db.query(ResumeStatus).filter(ResumeStatus.student_id == student_id).first()
        if not status:
            status = ResumeStatus(student_id=student_id)
            db.add(status)
            db.commit()
            db.refresh(status)
        return status

    @staticmethod
    def get_status(db: Session, student_id: UUID) -> Optional[ResumeStatus]:
        """Get resume status for a student."""
        return db.query(ResumeStatus).filter(ResumeStatus.student_id == student_id).first()

    @staticmethod
    def update_resume_info(
        db: Session,
        student_id: UUID,
        resume_url: str,
        has_resume: bool = True,
        resume_uploaded: bool = True,
    ) -> ResumeStatus:
        """Update resume information."""
        status = ResumeStatusService.get_or_create(db, student_id)
        status.resume_url = resume_url
        status.has_resume = has_resume
        status.resume_uploaded = resume_uploaded
        status.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(status)
        return status

    @staticmethod
    def update_ats_score(
        db: Session,
        student_id: UUID,
        ats_data: dict,
    ) -> ResumeStatus:
        """Update ATS score and analysis."""
        status = ResumeStatusService.get_or_create(db, student_id)
        
        # Update scalar fields
        status.ats_score = ats_data.get("ats_score")
        status.overall_assessment = ats_data.get("overall_assessment")
        status.formatting_score = ats_data.get("formatting_score")
        status.content_score = ats_data.get("content_score")
        status.keyword_score = ats_data.get("keyword_score")
        status.ats_calculated_at = datetime.utcnow()
        
        # Update JSONB fields (store as-is, they'll be serialized by SQLAlchemy)
        status.strengths = ats_data.get("strengths")
        status.weaknesses = ats_data.get("weaknesses")
        status.recommendations = ats_data.get("recommendations")
        status.keyword_analysis = ats_data.get("keyword_analysis")
        status.sections_analysis = ats_data.get("sections_analysis")
        status.extracted_skills = ats_data.get("extracted_skills")
        
        status.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(status)
        return status

    @staticmethod
    def to_dict(status: ResumeStatus) -> dict:
        """Convert ResumeStatus model to dict."""
        return {
            "id": str(status.id),
            "student_id": str(status.student_id),
            "has_resume": status.has_resume,
            "resume_uploaded": status.resume_uploaded,
            "resume_url": status.resume_url,
            "can_upload": status.can_upload,
            "ats_score": status.ats_score,
            "overall_assessment": status.overall_assessment,
            "formatting_score": status.formatting_score,
            "content_score": status.content_score,
            "keyword_score": status.keyword_score,
            "strengths": status.strengths,
            "weaknesses": status.weaknesses,
            "recommendations": status.recommendations,
            "keyword_analysis": status.keyword_analysis,
            "sections_analysis": status.sections_analysis,
            "extracted_skills": status.extracted_skills,
            "created_at": status.created_at.isoformat() if status.created_at else None,
            "updated_at": status.updated_at.isoformat() if status.updated_at else None,
            "ats_calculated_at": status.ats_calculated_at.isoformat() if status.ats_calculated_at else None,
        }

    @staticmethod
    def to_resume_status_response(status: ResumeStatus) -> dict:
        """Convert to resume status API response format."""
        return {
            "has_resume": status.has_resume,
            "resume_uploaded": status.resume_uploaded,
            "resume_url": status.resume_url,
            "last_updated": status.updated_at.isoformat() if status.updated_at else None,
            "can_upload": status.can_upload,
        }

    @staticmethod
    def to_ats_score_response(status: ResumeStatus) -> dict:
        """Convert to ATS score API response format."""
        response = {
            "ats_score": status.ats_score,
            "overall_assessment": status.overall_assessment,
            "strengths": status.strengths or [],
            "weaknesses": status.weaknesses or [],
            "keyword_analysis": status.keyword_analysis or {},
            "sections_analysis": status.sections_analysis or {},
            "recommendations": status.recommendations or [],
            "formatting_score": status.formatting_score,
            "content_score": status.content_score,
            "keyword_score": status.keyword_score,
            "extracted_skills": status.extracted_skills or {},
        }
        return response
