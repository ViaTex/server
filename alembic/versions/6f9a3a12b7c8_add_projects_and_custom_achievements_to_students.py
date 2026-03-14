"""Add projects and custom achievements to students

Revision ID: 6f9a3a12b7c8
Revises: 476502158574
Create Date: 2026-03-14

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "6f9a3a12b7c8"
down_revision: Union[str, None] = "476502158574"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "students",
        sa.Column(
            "projects",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "students",
        sa.Column(
            "custom_achievements",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("students", "custom_achievements")
    op.drop_column("students", "projects")
