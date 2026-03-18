"""Add profile vector and DES score to students

Revision ID: d4e5f6a7b8c9
Revises: 7c3a2d9f1b2e
Create Date: 2026-03-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "7c3a2d9f1b2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("students", sa.Column("profile_vector", Vector(384), nullable=True))
    op.add_column(
        "students",
        sa.Column(
            "current_des_score",
            sa.Numeric(precision=3, scale=2),
            nullable=False,
            server_default=sa.text("0.0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("students", "current_des_score")
    op.drop_column("students", "profile_vector")
