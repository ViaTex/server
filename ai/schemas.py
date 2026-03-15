from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List


class ResumeProject(BaseModel):
    title: str = ""
    description: str = ""
    technologies_used: List[str] = Field(default_factory=list)
    github_url: str = ""
    demo_url: str = ""
    start_date: str = ""
    end_date: str = ""


class ResumeParsedResponse(BaseModel):
    # Personal
    name: str = ""
    email: str = ""
    phone: str = ""
    dob: str = ""  # ISO-like if available (YYYY-MM-DD)
    gender: str = ""  # male/female/other if present

    # Location
    city: str = ""
    state: str = ""
    country: str = ""

    # Education
    institution: str = ""
    degree: str = ""
    branch: str = ""
    major: str = ""
    graduation_year: str = ""

    # Academics
    tenth_grade_percentage: str = ""
    twelfth_grade_percentage: str = ""
    btech_cgpa: str = ""

    # Skills / preferences
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    preferred_industry: str = ""
    job_roles_of_interest: List[str] = Field(default_factory=list)
    location_preferences: List[str] = Field(default_factory=list)
    language_proficiency: List[str] = Field(default_factory=list)

    # Experience
    extracurricular_activities: List[str] = Field(default_factory=list)
    internship_experience: List[str] = Field(default_factory=list)

    # Links
    linkedin_profile: str = ""
    github_profile: str = ""
    personal_website: str = ""

    # Generated
    bio: str = ""

    # Structured
    projects: List[ResumeProject] = Field(default_factory=list)
    custom_achievements: List[str] = Field(default_factory=list)
