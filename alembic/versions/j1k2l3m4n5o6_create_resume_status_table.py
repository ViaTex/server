"""Create resume_status table

Revision ID: j1k2l3m4n5o6
Revises: i9j0k1l2m3n4
Create Date: 2026-04-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create resume_status table."""
    op.create_table(
        "resume_status",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("has_resume", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("resume_uploaded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("resume_url", sa.String(length=1000), nullable=True),
        sa.Column("can_upload", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ats_score", sa.Integer(), nullable=True),
        sa.Column("overall_assessment", sa.String(length=2000), nullable=True),
        sa.Column("formatting_score", sa.Integer(), nullable=True),
        sa.Column("content_score", sa.Integer(), nullable=True),
        sa.Column("keyword_score", sa.Integer(), nullable=True),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("weaknesses", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("keyword_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sections_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extracted_skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ats_calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", name="uq_resume_status_student_id"),
    )
    op.create_index(
        "ix_resume_status_student_id",
        "resume_status",
        ["student_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema - drop resume_status table."""
    op.drop_index("ix_resume_status_student_id", table_name="resume_status")
    op.drop_table("resume_status")
