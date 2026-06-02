from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Date, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy import event
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import enum
import uuid

from app.core.database import Base


class UserType(str, enum.Enum):
    STUDENT = "student"
    MENTOR = "mentor"
    CORPORATE = "corporate"
    COLLEGE = "college"
    ADMIN = "admin"


class SessionUserType(str, enum.Enum):
    STUDENT = "STUDENT"
    MENTOR = "MENTOR"
    CORPORATE = "CORPORATE"
    COLLEGE = "COLLEGE"
    ADMIN = "ADMIN"


class SkillEvaluationStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    ASSIGNED = "assigned"
    UNDER_REVIEW = "under_review"
    VIVA_SCHEDULED = "viva_scheduled"
    VIVA_COMPLETED = "viva_completed"
    EVALUATED = "evaluated"


class SkillEvaluationVerdict(str, enum.Enum):
    EXCELLENT = "excellent"
    VERY_GOOD = "very_good"
    GOOD = "good"
    NEEDS_IMPROVEMENT = "needs_improvement"
    DID_NOT_PASS = "did_not_pass"

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
    profile_picture_url = Column(String(1000), nullable=True)
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
    
    experience = Column(JSONB, nullable=False, default=list)

    # Structured sections (stored inside the students table for now)
    projects = Column(JSONB, nullable=False, default=list)
    custom_achievements = Column(JSONB, nullable=False, default=list)
    
    linkedin_profile = Column(String(500), nullable=True)
    github_profile = Column(String(500), nullable=True)
    personal_website = Column(String(500), nullable=True)
    resume_url = Column(String(1000), nullable=True)

    has_accepted_terms = Column(Boolean, default=False, nullable=False)
    accepted_terms_version = Column(String(50), nullable=True)
    student_unique_id = Column(String(10), unique=True, index=True, nullable=True)

    current_des_score = Column(Numeric(4, 2), nullable=False, server_default="0.0")
    skill_profile = Column(JSONB, nullable=True)
    badge = Column(String(20), nullable=True)
    skill_profile = Column(JSONB, nullable=True)
    
    college_id = Column(String(255), nullable=True)
    exam_sessions = relationship("ExamSession", back_populates="student", cascade="all, delete-orphan")
    evaluations_received = relationship(
        "SkillEvaluation",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    profile_history_entries = relationship(
        "UserProfileHistory",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Mentor(BaseUser):
    __tablename__ = "mentors"

    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    current_role = Column(String(255), nullable=True)
    expertise_areas = Column(JSONB, nullable=False, default=list)
    experience_years = Column(Integer, nullable=True)
    motivation = Column(Text, nullable=True)
    average_rating = Column(Numeric(3, 2), nullable=False, server_default="0.0")

    skill_evaluations = relationship(
        "SkillEvaluation",
        back_populates="mentor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


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

    has_accepted_terms = Column(Boolean, default=False, nullable=False)
    accepted_terms_version = Column(String(50), nullable=True)
    

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


class SkillEvaluation(Base):
    __tablename__ = "skill_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mentor_id = Column(UUID(as_uuid=True), ForeignKey("mentors.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    status = Column(Enum(SkillEvaluationStatus, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=SkillEvaluationStatus.SUBMITTED)
    proposed_slots = Column(JSONB, nullable=False, default=list)
    confirmed_slot = Column(DateTime(timezone=True), nullable=True)
    viva_meeting_link = Column(String(1000), nullable=True)

    score_technical = Column(Integer, nullable=True)
    score_practical = Column(Integer, nullable=True)
    score_communication = Column(Integer, nullable=True)
    score_originality = Column(Integer, nullable=True)
    total_score = Column(Integer, nullable=True)
    verdict = Column(Enum(SkillEvaluationVerdict, values_callable=lambda obj: [e.value for e in obj]), nullable=True)
    feedback_strengths = Column(Text, nullable=True)
    feedback_improvements = Column(Text, nullable=True)

    student_rating_of_mentor = Column(Integer, nullable=True)
    student_technical_issues = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    mentor = relationship("Mentor", back_populates="skill_evaluations")
    student = relationship("Student", back_populates="evaluations_received")
    project = relationship("Project", primaryjoin="foreign(SkillEvaluation.project_id) == Project.id")


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    user_type = Column(Enum(SessionUserType), nullable=False)
    session_token = Column(String(500), nullable=False, unique=True)
    refresh_token = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_fingerprint = Column(String(255), nullable=True, index=True)
    device_label = Column(String(255), nullable=True)
    login_location = Column(String(255), nullable=True)
    trusted_device = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(String(255), nullable=True)
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
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    resend_count = Column(Integer, default=0, nullable=False)
    next_resend_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    otp_code = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuthAuditLog(Base):
    __tablename__ = "auth_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def _badge_from_des_score(score) -> str:
    try:
        value = float(score or 0.0)
    except Exception:
        value = 0.0

    if value < 3.0:
        return "Bronze"
    if value < 5.0:
        return "Silver"
    if value < 7.0:
        return "Gold"
    return "Diamond"


@event.listens_for(Student, "before_insert")
def set_badge_before_insert(_mapper, _connection, target):
    target.badge = _badge_from_des_score(target.current_des_score)


@event.listens_for(Student, "before_update")
def set_badge_before_update(_mapper, _connection, target):
    target.badge = _badge_from_des_score(target.current_des_score)
