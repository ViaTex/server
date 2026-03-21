"""Replace internship_experience with experience JSONB.

Revision ID: 5c8a9d0e1f2a
Revises: 1a2b3c4d5e7f
Create Date: 2026-03-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "5c8a9d0e1f2a"
down_revision: Union[str, None] = "1a2b3c4d5e7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    student_columns = {column["name"] for column in inspector.get_columns("students")}

    if "experience" not in student_columns:
        op.add_column(
            "students",
            sa.Column(
                "experience",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )
        op.alter_column("students", "experience", server_default=None)

    if "internship_experience" in student_columns:
        op.drop_column("students", "internship_experience")


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    student_columns = {column["name"] for column in inspector.get_columns("students")}

    if "internship_experience" not in student_columns:
        op.add_column("students", sa.Column("internship_experience", sa.Text(), nullable=True))

    if "experience" in student_columns:
        op.drop_column("students", "experience")
