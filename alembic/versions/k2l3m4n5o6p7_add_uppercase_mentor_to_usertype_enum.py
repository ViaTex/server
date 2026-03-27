"""Add uppercase MENTOR to usertype enum

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-03-27
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, None] = "j1k2l3m4n5o6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'usertype') THEN
                BEGIN
                    ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'MENTOR';
                EXCEPTION WHEN duplicate_object THEN
                    NULL;
                END;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    # PostgreSQL does not support dropping a single enum value safely in-place.
    pass
