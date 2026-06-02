from pydantic import BaseModel, EmailStr, Field, model_validator
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
    has_accepted_terms: bool = False
    accepted_terms_version: Optional[str] = None

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
    has_accepted_terms: bool = False
    accepted_terms_version: Optional[str] = None


class MentorRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    user_id: Optional[str] = None
    current_role: Optional[str] = None
    expertise_areas: Optional[List[str]] = None
    experience_years: Optional[int] = None
    motivation: Optional[str] = None

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
    user_type: Optional[str] = Field(None, description="Must be one of: student, mentor, corporate, college, admin")

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    code: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)


class ForgotPasswordStartRequest(BaseModel):
    identifier: Optional[str] = Field(None, min_length=3, max_length=255, description="Email or phone")
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    captcha_token: Optional[str] = None
    channel: str = Field(default="email", description="email or sms")

    @model_validator(mode="after")
    def normalize_identifier(self):
        if not self.identifier:
            self.identifier = str(self.email or self.phone or "").strip()
        if not self.identifier:
            raise ValueError("identifier or email or phone is required")
        return self


class ForgotPasswordOtpVerifyRequest(BaseModel):
    identifier: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    otp: Optional[str] = Field(None, min_length=6, max_length=6)
    code: Optional[str] = Field(None, min_length=6, max_length=6)
    captcha_token: Optional[str] = None

    @model_validator(mode="after")
    def normalize_fields(self):
        if not self.identifier:
            self.identifier = str(self.email or self.phone or "").strip()
        if not self.otp:
            self.otp = self.code
        if not self.identifier:
            raise ValueError("identifier or email or phone is required")
        if not self.otp:
            raise ValueError("otp or code is required")
        return self


class ForgotPasswordCompleteRequest(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=8)


class ResendOtpRequest(BaseModel):
    identifier: str
    channel: str = Field(default="email")


class EmailVerificationLinkRequest(BaseModel):
    token: str


class EmailVerificationOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ResendEmailVerificationRequest(BaseModel):
    email: EmailStr


class MailTestRequest(BaseModel):
    email: EmailStr
