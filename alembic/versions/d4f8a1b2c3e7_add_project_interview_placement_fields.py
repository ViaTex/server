"""add_project_interview_placement_fields

Revision ID: d4f8a1b2c3e7
Revises: (set to your latest revision id)
Create Date: 2026-05-28

Creates:
  - projects table
  - interviews table
  - placement columns on job_applications
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d4f8a1b2c3e7"
down_revision = "802de415524e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums ────────────────────────────────────────────────────────────────
    projectstatus = postgresql.ENUM(
        "pending_viva", "viva_scheduled", "viva_completed", "verified", "failed",
        name="projectstatus",
    )
    interviewtype = postgresql.ENUM(
        "technical", "culture_fit", "hr", "final",
        name="interviewtype",
    )
    interviewstatus = postgresql.ENUM(
        "proposed", "confirmed", "completed", "cancelled",
        name="interviewstatus",
    )
    interviewoutcome = postgresql.ENUM(
        "proceed", "reject", "hold", "offer",
        name="interviewoutcome",
    )

    # Let op.create_table create the enums automatically.

    # ── projects table ───────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("github_url", sa.String(1000), nullable=True),
        sa.Column("live_url", sa.String(1000), nullable=True),
        sa.Column("tech_stack", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("skill_domain", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending_viva", "viva_scheduled", "viva_completed", "verified", "failed",
                name="projectstatus",
            ),
            nullable=False,
            server_default="pending_viva",
        ),
        sa.Column("verified_badge", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── interviews table ─────────────────────────────────────────────────────
    op.create_table(
        "interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_applications.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "corporate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("corporates.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("proposed_slots", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="45"),
        sa.Column("meeting_link", sa.String(1000), nullable=True),
        sa.Column(
            "interview_type",
            sa.Enum("technical", "culture_fit", "hr", "final", name="interviewtype"),
            nullable=False,
            server_default="technical",
        ),
        sa.Column(
            "status",
            sa.Enum("proposed", "confirmed", "completed", "cancelled", name="interviewstatus"),
            nullable=False,
            server_default="proposed",
        ),
        sa.Column("interviewer_notes", sa.Text, nullable=True),
        sa.Column(
            "outcome",
            sa.Enum("proceed", "reject", "hold", "offer", name="interviewoutcome"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── Placement columns on job_applications ────────────────────────────────
    op.add_column("job_applications", sa.Column("placed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("job_applications", sa.Column("placed_by_corporate_name", sa.String(255), nullable=True))
    op.add_column("job_applications", sa.Column("placed_job_title", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("job_applications", "placed_job_title")
    op.drop_column("job_applications", "placed_by_corporate_name")
    op.drop_column("job_applications", "placed_at")

    op.drop_table("interviews")
    op.drop_table("projects")

    op.execute("DROP TYPE IF EXISTS interviewoutcome")
    op.execute("DROP TYPE IF EXISTS interviewstatus")
    op.execute("DROP TYPE IF EXISTS interviewtype")
    op.execute("DROP TYPE IF EXISTS projectstatus")
