"""Add terms acceptance and student unique ID

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-03-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("has_accepted_terms", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("students", sa.Column("accepted_terms_version", sa.String(length=50), nullable=True))
    op.add_column("students", sa.Column("student_unique_id", sa.String(length=10), nullable=True))
    op.create_unique_constraint("uq_students_student_unique_id", "students", ["student_unique_id"])

    op.add_column("corporates", sa.Column("has_accepted_terms", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("corporates", sa.Column("accepted_terms_version", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("corporates", "accepted_terms_version")
    op.drop_column("corporates", "has_accepted_terms")

    op.drop_constraint("uq_students_student_unique_id", "students", type_="unique")
    op.drop_column("students", "student_unique_id")
    op.drop_column("students", "accepted_terms_version")
    op.drop_column("students", "has_accepted_terms")
