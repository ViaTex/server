"""Student Profile Model - One-to-One relationship with User"""

import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING, Optional, List
from sqlalchemy import String, Boolean, Date, DateTime, Text, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class StudentInfo(Base):
    """
    Student profile information model.
    One-to-One relationship with User table.
    """
    
    __tablename__ = "student_info"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    # Foreign Key - One-to-One with User
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,  # Ensures One-to-One relationship
        nullable=False,
        index=True
    )
    
    # Profile Status
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Mandatory Profile Fields
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Male, Female, Other, Prefer not to say
    
    # Location (stored as JSON for flexibility)
    location: Mapped[Optional[dict]] = mapped_column(
        JSONB, 
        nullable=True,
        comment="JSON: {city, state, country, pincode}"
    )
    
    # Education - Array of education entries (min 1 required for completion)
    # Structure: [{degree, institution, field_of_study, start_year, end_year, grade, is_current}]
    education: Mapped[Optional[List[dict]]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="Array of education entries"
    )
    
    # Skills - Array of skills (min 3 required for completion)
    # Structure: [{name, proficiency_level, years_of_experience, category}]
    skills: Mapped[Optional[List[dict]]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="Array of skill entries"
    )
    
    # Projects - Array of project entries (optional)
    # Structure: [{id, title, short_description, detailed_paragraph, tech_stack[], links{github, demo}}]
    projects: Mapped[Optional[List[dict]]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="Array of project entries"
    )
    
    # Bio - AI-generated or manually edited
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI-generated or manually edited bio"
    )
    bio_is_ai_generated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the bio was AI-generated"
    )
    bio_is_edited: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the AI bio was edited by user"
    )
    
    # Profile completion percentage (useful for UI progress bars)
    completion_percentage: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Profile completion percentage (0-100)"
    )
    
    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationship back to User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="student_info",
        lazy="joined"
    )
    
    def __repr__(self):
        return f"<StudentInfo(id={self.id}, user_id={self.user_id}, is_complete={self.is_complete})>"
    
    def calculate_completion_percentage(self) -> int:
        """Calculate profile completion percentage based on mandatory fields"""
        total_fields = 5  # DOB, Gender, Location, Education (min 1), Skills (min 3)
        completed = 0
        
        if self.date_of_birth:
            completed += 1
        if self.gender:
            completed += 1
        if self.location and all(k in self.location for k in ['city', 'state', 'country']):
            completed += 1
        if self.education and len(self.education) >= 1:
            completed += 1
        if self.skills and len(self.skills) >= 3:
            completed += 1
        
        return int((completed / total_fields) * 100)
    
    def check_mandatory_fields_complete(self) -> tuple[bool, list[str]]:
        """
        Check if all mandatory fields are complete.
        Returns (is_complete, list_of_missing_fields)
        """
        missing_fields = []
        
        if not self.date_of_birth:
            missing_fields.append("date_of_birth")
        if not self.gender:
            missing_fields.append("gender")
        if not self.location or not all(k in self.location for k in ['city', 'state', 'country']):
            missing_fields.append("location (city, state, country required)")
        if not self.education or len(self.education) < 1:
            missing_fields.append("education (minimum 1 entry required)")
        if not self.skills or len(self.skills) < 3:
            missing_fields.append("skills (minimum 3 skills required)")
        
        return len(missing_fields) == 0, missing_fields
