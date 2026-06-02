from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ProjectStatus(str, enum.Enum):
    PENDING_VIVA = "pending_viva"
    VIVA_SCHEDULED = "viva_scheduled"
    VIVA_COMPLETED = "viva_completed"
    VERIFIED = "verified"
    FAILED = "failed"


project_status_enum = Enum(
    ProjectStatus,
    name="projectstatus",
    values_callable=lambda enum_cls: [item.value for item in enum_cls],
)


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    github_url = Column(String(1000), nullable=True)
    live_url = Column(String(1000), nullable=True)
    tech_stack = Column(JSONB, nullable=False, default=list)   # ["React", "Node.js"]
    skill_domain = Column(String(255), nullable=True)          # "Frontend", "Data Science"

    status = Column(project_status_enum, nullable=False, default=ProjectStatus.PENDING_VIVA)
    verified_badge = Column(String(255), nullable=True)        # "Verified React Developer ✓"

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    student = relationship("Student", backref="projects_formal")
