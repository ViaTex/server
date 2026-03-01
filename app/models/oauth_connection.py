import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class OAuthConnection(Base):
    """OAuth SSO connections linking Google/LinkedIn to user accounts"""
    
    __tablename__ = "oauth_connections"
    
    # Composite unique constraint on provider and provider_id
    __table_args__ = (
        UniqueConstraint('provider', 'provider_id', name='uq_provider_provider_id'),
    )
    
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
    
    # OAuth Provider Information
    provider: Mapped[str] = mapped_column(
        String(50), 
        nullable=False
    )  # 'google' or 'linkedin'
    
    provider_id: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )  # Unique ID from OAuth provider
    
    # Metadata
    provider_email: Mapped[str] = mapped_column(String(255), nullable=True)
    provider_name: Mapped[str] = mapped_column(String(255), nullable=True)
    access_token: Mapped[str] = mapped_column(String(500), nullable=True)  # Optional: store for API access
    refresh_token: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # Audit
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
    user: Mapped["User"] = relationship("User", back_populates="oauth_connections")
    
    def __repr__(self):
        return f"<OAuthConnection(id={self.id}, provider={self.provider}, user_id={self.user_id})>"
