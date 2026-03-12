from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import date
from app.models.user import Gender

class StudentProfileBase(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    institution: Optional[str] = None
    degree: Optional[str] = None
    branch: Optional[str] = None
    graduation_year: Optional[int] = None
    major: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[Gender] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    tenth_grade_percentage: Optional[float] = None
    twelfth_grade_percentage: Optional[float] = None
    btech_cgpa: Optional[float] = None
    technical_skills: Optional[str] = None
    soft_skills: Optional[str] = None
    certifications: Optional[str] = None
    preferred_industry: Optional[str] = None
    job_roles_of_interest: Optional[str] = None
    location_preferences: Optional[str] = None
    language_proficiency: Optional[str] = None
    extracurricular_activities: Optional[str] = None
    internship_experience: Optional[str] = None
    project_details: Optional[str] = None
    linkedin_profile: Optional[str] = None
    github_profile: Optional[str] = None
    personal_website: Optional[str] = None

class StudentProfileUpdate(StudentProfileBase):
    pass

class StudentProfileResponse(StudentProfileBase):
    id: str
    email: EmailStr

    @field_validator("id", mode="before")
    @classmethod
    def id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
