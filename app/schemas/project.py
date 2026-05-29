from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl

from app.models.project import ProjectStatus


class ProjectCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    github_url: Optional[str] = Field(None, max_length=1000)
    live_url: Optional[str] = Field(None, max_length=1000)
    tech_stack: list[str] = Field(default_factory=list)
    skill_domain: Optional[str] = Field(None, max_length=255)


class ProjectStatusUpdate(BaseModel):
    status: ProjectStatus
    verified_badge: Optional[str] = Field(None, max_length=255)


class ProjectResponse(BaseModel):
    id: str
    student_id: str
    title: str
    description: Optional[str] = None
    github_url: Optional[str] = None
    live_url: Optional[str] = None
    tech_stack: list[str] = Field(default_factory=list)
    skill_domain: Optional[str] = None
    status: ProjectStatus
    verified_badge: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
