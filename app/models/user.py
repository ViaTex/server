import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.oauth_connection import OAuthConnection
    from app.models.refresh_token import RefreshToken
    from app.models.otp import OTP


class User(Base):
    """User model for authentication and authorization"""
    
    __tablename__ = "users"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )
    
    # Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)  # Nullable for OAuth-only users
    
    # Account Information
    account_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False
    )  # Individual or Institutional
    role: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        index=True
    )  # Student, Mentor, TPO, Corporate HR
    
    # Verification Status
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    account_status: Mapped[str] = mapped_column(
        String(20), 
        default="pending", 
        nullable=False
    )  # pending, active, suspended
    
    # Security
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Audit
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    oauth_connections: Mapped[list["OAuthConnection"]] = relationship(
        "OAuthConnection", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    otps: Mapped[list["OTP"]] = relationship(
        "OTP", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
