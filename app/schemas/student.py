from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
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


WorkMode = Literal["onsite", "hybrid", "remote"]
ExperienceType = Literal["internship", "full_time", "other"]


class ExperienceEntry(BaseModel):
    id: Optional[str] = None
    company_name: Optional[str] = None
    role: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    major_project: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    work_mode: WorkMode = "onsite"
    experience_type: ExperienceType = "other"

    @field_validator(
        "company_name",
        "role",
        "major_project",
        "start_date",
        "end_date",
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

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_skills(cls, v: Any):
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

EducationLevel = Literal["UG", "PG", "Diploma", "12th", "10th", "Other"]


class StudentEducation(BaseModel):
    id: Optional[str] = None
    level: EducationLevel
    custom_level: Optional[str] = None
    institution: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    score: Optional[str] = None
    description: Optional[str] = None

    @field_validator(
        "custom_level",
        "institution",
        "start_date",
        "end_date",
        "score",
        "description",
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

    @field_validator("level", mode="before")
    @classmethod
    def normalize_level(cls, v: Any):
        if isinstance(v, str):
            s = v.strip().lower().replace(" ", "")
            if s in ("ug", "undergraduate", "btech", "b.tech", "bachelor"):
                return "UG"
            if s in ("pg", "postgraduate", "mtech", "m.tech", "master"):
                return "PG"
            if s in ("diploma",):
                return "Diploma"
            if s in ("12th", "12", "xii"):
                return "12th"
            if s in ("10th", "10", "x"):
                return "10th"
            if s in ("other",):
                return "Other"
        return v

    @model_validator(mode="after")
    def validate_required_fields(self):
        if not self.institution:
            raise ValueError("Institution is required")
        if self.level == "Other" and not self.custom_level:
            raise ValueError("custom_level is required when level is Other")
        return self

class StudentProfileBase(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[Gender] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    technical_skills: Optional[str] = None
    soft_skills: Optional[str] = None
    certifications: Optional[str] = None
    preferred_industry: Optional[str] = None
    job_roles_of_interest: Optional[str] = None
    location_preferences: Optional[str] = None
    language_proficiency: Optional[str] = None
    extracurricular_activities: Optional[str] = None
    experience: Optional[List[ExperienceEntry]] = None
    linkedin_profile: Optional[str] = None
    github_profile: Optional[str] = None
    personal_website: Optional[str] = None
    resume_url: Optional[str] = None
    profile_picture_url: Optional[str] = None
    current_des_score: Optional[float] = None
    badge: Optional[str] = None

    # New structured profile sections
    education: Optional[List[StudentEducation]] = None
    projects: Optional[List[StudentProject]] = None
    custom_achievements: Optional[List[CustomAchievement]] = None

class StudentProfileUpdate(StudentProfileBase):
    pass

class StudentProfileResponse(StudentProfileBase):
    id: str
    email: EmailStr
    student_unique_id: Optional[str] = None

    @field_validator("id", mode="before")
    @classmethod
    def id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True
