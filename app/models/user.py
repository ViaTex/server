from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Date, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from datetime import datetime
import enum
import uuid

from app.core.database import Base


class UserType(str, enum.Enum):
    STUDENT = "student"
    CORPORATE = "corporate"
    COLLEGE = "college"
    ADMIN = "admin"

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class BaseUser(Base):
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)


class Student(BaseUser):
    __tablename__ = "students"
    
    bio = Column(Text, nullable=True)
    
    dob = Column(Date, nullable=True)
    gender = Column(Enum(Gender), nullable=True)
    country = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Education history (JSON-based, dynamic)
    education = Column(JSONB, nullable=False, default=list)
    
    technical_skills = Column(Text, nullable=True)
    soft_skills = Column(Text, nullable=True)
    certifications = Column(Text, nullable=True)
    preferred_industry = Column(String(255), nullable=True)
    job_roles_of_interest = Column(String(255), nullable=True)
    location_preferences = Column(String(255), nullable=True)
    language_proficiency = Column(Text, nullable=True)
    extracurricular_activities = Column(Text, nullable=True)
    
    internship_experience = Column(Text, nullable=True)

    # Structured sections (stored inside the students table for now)
    projects = Column(JSONB, nullable=False, default=list)
    custom_achievements = Column(JSONB, nullable=False, default=list)
    
    linkedin_profile = Column(String(500), nullable=True)
    github_profile = Column(String(500), nullable=True)
    personal_website = Column(String(500), nullable=True)
    resume_url = Column(String(1000), nullable=True)

    profile_vector = Column(Vector(384), nullable=True)
    current_des_score = Column(Numeric(3, 2), nullable=False, server_default="0.0")
    
    college_id = Column(String(255), nullable=True)


class Corporate(BaseUser):
    __tablename__ = "corporates"
    
    company_name = Column(String(255), nullable=False)
    website_url = Column(String(500), nullable=True)
    industry = Column(String(255), nullable=True)
    company_size = Column(String(50), nullable=True)
    founded_year = Column(Integer, nullable=True)
    
    contact_person = Column(String(255), nullable=True)
    contact_designation = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    
    description = Column(Text, nullable=True)
    company_type = Column(String(100), nullable=True)
    

class College(BaseUser):
    __tablename__ = "colleges"
    
    college_name = Column(String(255), nullable=False)
    website_url = Column(String(500), nullable=True)
    institute_type = Column(String(100), nullable=True)
    established_year = Column(Integer, nullable=True)
    
    contact_person_name = Column(String(255), nullable=True)
    contact_designation = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    
    courses_offered = Column(Text, nullable=True)
    branch = Column(String(255), nullable=True)
    college_id = Column(String(255), nullable=True)


class Admin(BaseUser):
    __tablename__ = "admins"
    role = Column(String(100), default="admin")


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    user_type = Column(Enum(UserType), nullable=False)
    session_token = Column(String(500), nullable=False, unique=True)
    refresh_token = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())


class EmailOTP(Base):
    __tablename__ = "email_otps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
