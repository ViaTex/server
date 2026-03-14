from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Literal, Any
from datetime import date
from app.models.user import Gender


class StudentProject(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    skills_used: List[str] = Field(default_factory=list)
    technologies_used: List[str] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    project_url: Optional[str] = None
    github_url: Optional[str] = None
    demo_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    status: Literal["completed", "in_progress"] = "in_progress"

    @field_validator(
        "title",
        "description",
        "start_date",
        "end_date",
        "project_url",
        "github_url",
        "demo_url",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, v: Any):
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s or None
        return v

    @field_validator("skills_used", "technologies_used", "images", mode="before")
    @classmethod
    def normalize_string_list(cls, v: Any):
        if v is None:
            return []
        if not isinstance(v, list):
            return []
        out: List[str] = []
        for item in v:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    out.append(s)
        return out

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any):
        if v is None:
            return "in_progress"
        if isinstance(v, str):
            s = v.strip().lower().replace(" ", "_")
            if s in ("completed",):
                return "completed"
            if s in ("in_progress", "inprogress"):
                return "in_progress"
        return "in_progress"


class CustomAchievement(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    category: Literal["Certification", "Blog", "Research", "Other"] = "Other"
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    date: Optional[str] = None

    @field_validator("title", "description", "url", "date", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Any):
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s or None
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: Any):
        if v is None:
            return []
        if not isinstance(v, list):
            return []
        out: List[str] = []
        for item in v:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    out.append(s)
        return out

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
    resume_url: Optional[str] = None

    # New structured profile sections
    projects: Optional[List[StudentProject]] = None
    custom_achievements: Optional[List[CustomAchievement]] = None

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
