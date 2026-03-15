"""Drop project_details from students.

Revision ID: 9f2a1b3c4d5e
Revises: 6f9a3a12b7c8
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9f2a1b3c4d5e"
down_revision = "6f9a3a12b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("students", "project_details")


def downgrade() -> None:
    op.add_column("students", sa.Column("project_details", sa.Text(), nullable=True))
