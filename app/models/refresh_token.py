import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base):
    """Refresh tokens for 30-day session persistence"""
    
    __tablename__ = "refresh_tokens"
    
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
    
    # Token Information
    token: Mapped[str] = mapped_column(
        String(500), 
        unique=True, 
        nullable=False,
        index=True
    )
    
    # Expiration and Revocation
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Security Audit
    device_ip: Mapped[str] = mapped_column(String(45), nullable=True)  # IPv6 max length
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
    
    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)"""
        return not self.is_expired and not self.is_revoked
