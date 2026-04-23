"""Create user_profile_history and drop deprecated student vector/profile columns.

Revision ID: 1a2b3c4d5e7f
Revises: 3b4c5d6e7f80
Create Date: 2026-03-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "1a2b3c4d5e7f"
down_revision: Union[str, None] = "3b4c5d6e7f80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if not inspector.has_table("user_profile_history"):
        op.create_table(
            "user_profile_history",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("profile_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("embedding", Vector(384), nullable=False),
            sa.Column("change_type", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["students.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_user_profile_history_user_id",
            "user_profile_history",
            ["user_id"],
            unique=False,
        )

    student_columns = {column["name"] for column in inspector.get_columns("students")}

    if "profile_vector" in student_columns:
        op.drop_column("students", "profile_vector")



def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    student_columns = {column["name"] for column in inspector.get_columns("students")}

    if "profile_vector" not in student_columns:
        op.add_column("students", sa.Column("profile_vector", Vector(384), nullable=True))
    if "skill_profile" not in student_columns:
        op.add_column("students", sa.Column("skill_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    if inspector.has_table("user_profile_history"):
        op.drop_index("ix_user_profile_history_user_id", table_name="user_profile_history")
        op.drop_table("user_profile_history")
