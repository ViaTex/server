"""Add exam_responses table and normalize exam_sessions.

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e7f
Create Date: 2026-03-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2b3c4d5e6f7a"
down_revision: Union[str, None] = "1a2b3c4d5e7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if inspector.has_table("exam_sessions"):
        with op.batch_alter_table("exam_sessions") as batch_op:
            batch_op.add_column(sa.Column("total_des_score", sa.Numeric(precision=6, scale=2), nullable=True))
            batch_op.add_column(sa.Column("performance_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
            batch_op.add_column(sa.Column("current_step", sa.String(length=32), nullable=False, server_default="SECTION_A"))
            batch_op.drop_column("exam_json")

        op.execute("ALTER TABLE exam_sessions ALTER COLUMN current_step DROP DEFAULT")

    if not inspector.has_table("exam_responses"):
        op.create_table(
            "exam_responses",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("section_type", sa.String(length=32), nullable=False),
            sa.Column("question_text", sa.Text(), nullable=False),
            sa.Column("user_response", sa.Text(), nullable=False),
            sa.Column("transcript", sa.Text(), nullable=True),
            # Upgraded to JSONB for multi-topic production scoring (1.00 - 10.00 scales)
            sa.Column("ai_score", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("mentor_score", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("hints_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_exam_responses_session_id"), "exam_responses", ["session_id"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if inspector.has_table("exam_responses"):
        op.drop_index(op.f("ix_exam_responses_session_id"), table_name="exam_responses")
        op.drop_table("exam_responses")

    if inspector.has_table("exam_sessions"):
        with op.batch_alter_table("exam_sessions") as batch_op:
            batch_op.add_column(sa.Column("exam_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
            batch_op.drop_column("current_step")
            batch_op.drop_column("performance_snapshot")
            batch_op.drop_column("total_des_score")