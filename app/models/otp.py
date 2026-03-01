import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.models.user import User


class OTP(Base):
    """OTP codes for email and phone verification"""
    
    __tablename__ = "otps"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Foreign Key to User
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # OTP Information
    otp_code: Mapped[str] = mapped_column(String(10), nullable=False)
    type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )  # 'email_verify', 'phone_verify', 'password_reset'
    
    # Expiration and Usage
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False
    )
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Attempt Tracking
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="otps")
    
    def __repr__(self):
        return f"<OTP(id={self.id}, user_id={self.user_id}, type={self.type}, used={self.used})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if OTP is expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if OTP is valid (not expired, not used, attempts < max)"""
        return (
            not self.is_expired 
            and not self.used 
            and self.attempts < settings.OTP_MAX_ATTEMPTS
        )
