from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class CorporateProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    company_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    contact_person: Optional[str] = Field(None, max_length=255)
    contact_designation: Optional[str] = Field(None, max_length=255)
    website_url: Optional[str] = Field(None, max_length=500)
    industry: Optional[str] = Field(None, max_length=255)
    company_size: Optional[str] = Field(None, max_length=50)
    founded_year: Optional[int] = Field(None, ge=1900, le=2100)
    company_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    address: Optional[str] = None


class CorporateProfileResponse(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    bio: Optional[str] = None
    company_name: Optional[str] = None
    phone: Optional[str] = None
    contact_person: Optional[str] = None
    contact_designation: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    founded_year: Optional[int] = None
    company_type: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None

    class Config:
        from_attributes = True
