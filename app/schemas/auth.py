from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date
from app.models.user import Gender

class StudentRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    institution: Optional[str] = None
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
    experience: Optional[List[dict]] = None
    linkedin_profile: Optional[str] = None
    github_profile: Optional[str] = None
    personal_website: Optional[str] = None
    college_id: Optional[str] = None

class CorporateRegisterRequest(BaseModel):
    company_name: str
    email: EmailStr
    password: str
    website_url: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    founded_year: Optional[int] = None
    contact_person: Optional[str] = None
    contact_designation: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    company_type: Optional[str] = None

class CollegeRegisterRequest(BaseModel):
    college_name: Optional[str] = None
    email: EmailStr
    password: str
    website_url: Optional[str] = None
    institute_type: Optional[str] = None
    established_year: Optional[int] = None
    contact_person_name: Optional[str] = None
    contact_designation: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    courses_offered: Optional[str] = None
    branch: Optional[str] = None
    college_id: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    user_type: str = Field(..., description="Must be one of: student, corporate, college, admin")

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    code: str
