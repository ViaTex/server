"""Add exam review assignments

Revision ID: m3n4o5p6q7r8
Revises: k2l3m4n5o6p7
Create Date: 2026-04-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "m3n4o5p6q7r8"
down_revision: Union[str, None] = "k2l3m4n5o6p7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if inspector.has_table("exam_review_assignments"):
        return

    op.create_table(
        "exam_review_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mentor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mentor_id"], ["mentors.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(
        "ix_exam_review_assignments_session_id",
        "exam_review_assignments",
        ["session_id"],
        unique=True,
    )
    op.create_index(
        "ix_exam_review_assignments_mentor_id",
        "exam_review_assignments",
        ["mentor_id"],
        unique=False,
    )
    op.create_index(
        "ix_exam_review_assignments_status",
        "exam_review_assignments",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if not inspector.has_table("exam_review_assignments"):
        return

    op.drop_index("ix_exam_review_assignments_status", table_name="exam_review_assignments")
    op.drop_index("ix_exam_review_assignments_mentor_id", table_name="exam_review_assignments")
    op.drop_index("ix_exam_review_assignments_session_id", table_name="exam_review_assignments")
    op.drop_table("exam_review_assignments")
