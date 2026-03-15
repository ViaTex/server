"""Create resume_embeddings table (pgvector)

Revision ID: d7a3f0c9b1e2
Revises: 9f2a1b3c4d5e
Create Date: 2026-03-15

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "d7a3f0c9b1e2"
down_revision: Union[str, None] = "9f2a1b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "resume_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "student_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("students.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_resume_embeddings_student_id",
        "resume_embeddings",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        "ix_resume_embeddings_student_id_section",
        "resume_embeddings",
        ["student_id", "section"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_resume_embeddings_student_id_section", table_name="resume_embeddings")
    op.drop_index("ix_resume_embeddings_student_id", table_name="resume_embeddings")
    op.drop_table("resume_embeddings")
