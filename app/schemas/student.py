"""Pydantic schemas for Student Profile"""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
import re


# ============= Nested Schemas =============

class LocationSchema(BaseModel):
    """Location information schema"""
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=1, max_length=100)
    pincode: Optional[str] = Field(None, max_length=20)
    
    model_config = {"from_attributes": True}


class LocationUpdateSchema(BaseModel):
    """Location update schema (all fields optional)"""
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=1, max_length=100)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    pincode: Optional[str] = Field(None, max_length=20)


class EducationSchema(BaseModel):
    """Education entry schema"""
    degree: str = Field(..., min_length=1, max_length=200)
    institution: str = Field(..., min_length=1, max_length=300)
    field_of_study: Optional[str] = Field(None, max_length=200)
    start_year: int = Field(..., ge=1950, le=2100)
    end_year: Optional[int] = Field(None, ge=1950, le=2100)
    grade: Optional[str] = Field(None, max_length=50)  # GPA, percentage, etc.
    is_current: bool = Field(default=False)
    
    @field_validator("end_year")
    @classmethod
    def validate_end_year(cls, v, info):
        if v is not None and "start_year" in info.data:
            if v < info.data["start_year"]:
                raise ValueError("End year must be greater than or equal to start year")
        return v
    
    model_config = {"from_attributes": True}


class SkillSchema(BaseModel):
    """Skill entry schema"""
    name: str = Field(..., min_length=1, max_length=100)
    proficiency_level: Optional[str] = Field(
        None, 
        pattern="^(Beginner|Intermediate|Advanced|Expert)$"
    )
    years_of_experience: Optional[float] = Field(None, ge=0, le=50)
    category: Optional[str] = Field(None, max_length=100)  # e.g., "Programming", "Design", "Management"
    
    model_config = {"from_attributes": True}


class ProjectLinksSchema(BaseModel):
    """Project links schema"""
    github: Optional[str] = Field(None, max_length=500)
    demo: Optional[str] = Field(None, max_length=500)
    
    @field_validator("github", "demo")
    @classmethod
    def validate_url(cls, v):
        if v is not None and v.strip():
            url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            if not re.match(url_pattern, v, re.IGNORECASE):
                raise ValueError("Invalid URL format")
        return v


class ProjectSchema(BaseModel):
    """Project entry schema"""
    id: Optional[UUID] = Field(None, description="Project ID, auto-generated if not provided")
    title: str = Field(..., min_length=1, max_length=200)
    short_description: str = Field(..., min_length=10, max_length=500)
    detailed_paragraph: Optional[str] = Field(None, max_length=5000)
    tech_stack: List[str] = Field(default_factory=list, max_length=20)
    links: Optional[ProjectLinksSchema] = None
    
    @field_validator("tech_stack")
    @classmethod
    def validate_tech_stack(cls, v):
        if v:
            # Remove duplicates and empty strings
            cleaned = list(set(item.strip() for item in v if item.strip()))
            return cleaned
        return v
    
    model_config = {"from_attributes": True}


# ============= Request Schemas =============

class StudentProfileWizardRequest(BaseModel):
    """
    Unified request schema for creating/updating student profile via wizard.
    Supports both manual input and AI-generated draft data.
    Validation triggers only on final save (not draft).
    """
    # Basic Info
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, pattern="^(Male|Female|Other|Prefer not to say)$")
    location: Optional[LocationSchema] = None
    
    # Education (min 1 required for final save)
    education: Optional[List[EducationSchema]] = Field(default_factory=list)
    
    # Skills (min 3 required for final save)
    skills: Optional[List[SkillSchema]] = Field(default_factory=list)
    
    # Projects (optional)
    projects: Optional[List[ProjectSchema]] = Field(default_factory=list)
    
    # Bio
    bio: Optional[str] = Field(None, max_length=5000)
    bio_is_ai_generated: bool = Field(default=False)
    
    # Save mode: draft or final
    is_draft: bool = Field(
        default=True,
        description="If True, save as draft without mandatory field validation. If False, validate all mandatory fields."
    )
    
    @model_validator(mode="after")
    def validate_mandatory_fields_on_final_save(self):
        """Only validate mandatory fields when saving as final (not draft)"""
        if not self.is_draft:
            missing_fields = []
            
            if not self.date_of_birth:
                missing_fields.append("date_of_birth")
            if not self.gender:
                missing_fields.append("gender")
            if not self.location:
                missing_fields.append("location")
            if not self.education or len(self.education) < 1:
                missing_fields.append("education (minimum 1 entry required)")
            if not self.skills or len(self.skills) < 3:
                missing_fields.append("skills (minimum 3 skills required)")
            
            if missing_fields:
                raise ValueError(f"Missing mandatory fields for profile completion: {', '.join(missing_fields)}")
        
        return self
    
    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v):
        if v is not None:
            today = date.today()
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age < 13:
                raise ValueError("User must be at least 13 years old")
            if age > 100:
                raise ValueError("Invalid date of birth")
        return v


class StudentProfileUpdateRequest(BaseModel):
    """
    Request schema for partial profile updates.
    All fields are optional - only provided fields will be updated.
    """
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, pattern="^(Male|Female|Other|Prefer not to say)$")
    location: Optional[LocationUpdateSchema] = None
    
    # For arrays, None means no change, empty list means clear
    education: Optional[List[EducationSchema]] = None
    skills: Optional[List[SkillSchema]] = None
    projects: Optional[List[ProjectSchema]] = None
    
    bio: Optional[str] = Field(None, max_length=5000)
    bio_is_ai_generated: Optional[bool] = None
    
    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v):
        if v is not None:
            today = date.today()
            age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
            if age < 13:
                raise ValueError("User must be at least 13 years old")
            if age > 100:
                raise ValueError("Invalid date of birth")
        return v


class AddSkillRequest(BaseModel):
    """Request to add a single skill"""
    skill: SkillSchema


class AddProjectRequest(BaseModel):
    """Request to add a single project"""
    project: ProjectSchema


class AddEducationRequest(BaseModel):
    """Request to add a single education entry"""
    education: EducationSchema


class UpdateBioRequest(BaseModel):
    """Request to update bio"""
    bio: str = Field(..., max_length=5000)
    is_ai_generated: bool = Field(default=False)


# ============= Response Schemas =============

class StudentProfileResponse(BaseModel):
    """Response schema for student profile"""
    id: UUID
    user_id: UUID
    
    # Status
    is_complete: bool
    is_draft: bool
    completion_percentage: int
    
    # Profile Data
    date_of_birth: Optional[date]
    gender: Optional[str]
    location: Optional[dict]
    education: Optional[List[dict]]
    skills: Optional[List[dict]]
    projects: Optional[List[dict]]
    
    # Bio
    bio: Optional[str]
    bio_is_ai_generated: bool
    bio_is_edited: bool
    
    # Audit
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class StudentProfileSummaryResponse(BaseModel):
    """Lightweight summary response for profile"""
    id: UUID
    user_id: UUID
    is_complete: bool
    is_draft: bool
    completion_percentage: int
    has_bio: bool
    skill_count: int
    project_count: int
    education_count: int
    
    model_config = {"from_attributes": True}


class ProfileCompletionStatusResponse(BaseModel):
    """Response showing profile completion status"""
    is_complete: bool
    completion_percentage: int
    missing_fields: List[str]
    
    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Simple message response"""
    message: str
    detail: Optional[str] = None


class ProjectDeleteResponse(BaseModel):
    """Response for project deletion"""
    message: str
    deleted_project_id: UUID
    remaining_projects_count: int
