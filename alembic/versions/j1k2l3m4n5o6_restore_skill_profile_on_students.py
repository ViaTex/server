"""Restore skill_profile on students.

Revision ID: j1k2l3m4n5o6
Revises: g2h3i4j5k6l7
Create Date: 2026-04-15

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if inspector.has_table("students"):
        existing_columns = {col["name"] for col in inspector.get_columns("students")}
        if "skill_profile" not in existing_columns:
            op.add_column("students", sa.Column("skill_profile", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if inspector.has_table("students"):
        existing_columns = {col["name"] for col in inspector.get_columns("students")}
        if "skill_profile" in existing_columns:
            op.drop_column("students", "skill_profile")
