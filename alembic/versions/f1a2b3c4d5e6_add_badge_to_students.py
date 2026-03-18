"""Add badge to students

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-03-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("badge", sa.String(length=20), nullable=True))

    op.execute(
        """
        UPDATE students
        SET badge = CASE
            WHEN COALESCE(current_des_score, 0.0) < 3.0 THEN 'Bronze'
            WHEN COALESCE(current_des_score, 0.0) < 5.0 THEN 'Silver'
            WHEN COALESCE(current_des_score, 0.0) < 7.0 THEN 'Gold'
            ELSE 'Diamond'
        END
        """
    )


def downgrade() -> None:
    op.drop_column("students", "badge")
