"""Add ai_feedback and mentor_feedback to exam_responses.

Revision ID: g2h3i4j5k6l7
Revises: c6ba0a089662
Create Date: 2026-03-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "g2h3i4j5k6l7"
down_revision: Union[str, None] = "c6ba0a089662"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if inspector.has_table("exam_responses"):
        existing_columns = {col["name"] for col in inspector.get_columns("exam_responses")}
        if "ai_feedback" not in existing_columns:
            op.add_column("exam_responses", sa.Column("ai_feedback", postgresql.JSONB(), nullable=True))
        if "mentor_feedback" not in existing_columns:
            op.add_column("exam_responses", sa.Column("mentor_feedback", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if inspector.has_table("exam_responses"):
        existing_columns = {col["name"] for col in inspector.get_columns("exam_responses")}
        if "mentor_feedback" in existing_columns:
            op.drop_column("exam_responses", "mentor_feedback")
        if "ai_feedback" in existing_columns:
            op.drop_column("exam_responses", "ai_feedback")
