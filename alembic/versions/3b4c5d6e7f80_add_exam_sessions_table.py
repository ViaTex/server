"""Add exam_sessions table

Revision ID: 3b4c5d6e7f80
Revises: a7b8c9d0e1f2
Create Date: 2026-03-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "3b4c5d6e7f80"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if inspector.has_table("exam_sessions"):
        return

    op.create_table(
        "exam_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("exam_level", sa.String(length=100), nullable=False),
        sa.Column("exam_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("growth_rate", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("is_passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exam_sessions_student_id"), "exam_sessions", ["student_id"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if not inspector.has_table("exam_sessions"):
        return

    op.drop_index(op.f("ix_exam_sessions_student_id"), table_name="exam_sessions")
    op.drop_table("exam_sessions")
