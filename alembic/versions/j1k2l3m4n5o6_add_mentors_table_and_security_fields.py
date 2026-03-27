"""Add mentors table and security fields

Revision ID: j1k2l3m4n5o6
Revises: i9j0k1l2m3n4
Create Date: 2026-03-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'usertype') THEN
                BEGIN
                    ALTER TYPE usertype ADD VALUE IF NOT EXISTS 'mentor';
                EXCEPTION WHEN duplicate_object THEN
                    NULL;
                END;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mentorverificationstatus') THEN
                CREATE TYPE mentorverificationstatus AS ENUM ('Unverified', 'Pending', 'Verified', 'Rejected');
            END IF;
        END
        $$;
        """
    )

    mentor_verification_status = postgresql.ENUM(
        "Unverified",
        "Pending",
        "Verified",
        "Rejected",
        name="mentorverificationstatus",
        create_type=False,
    )

    op.create_table(
        "mentors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("mentor_id", sa.String(length=10), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email_id", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_phone_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("current_company", sa.String(length=255), nullable=True),
        sa.Column("total_experience", sa.Integer(), nullable=False),
        sa.Column("domain_expertise", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("verification_status", mentor_verification_status, nullable=False, server_default=sa.text("'Unverified'")),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mentor_id", name="uq_mentors_mentor_id"),
        sa.UniqueConstraint("email_id", name="uq_mentors_email_id"),
    )

    op.create_index("ix_mentors_mentor_id", "mentors", ["mentor_id"], unique=True)
    op.create_index("ix_mentors_email_id", "mentors", ["email_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_mentors_email_id", table_name="mentors")
    op.drop_index("ix_mentors_mentor_id", table_name="mentors")
    op.drop_table("mentors")

    op.execute("DROP TYPE IF EXISTS mentorverificationstatus")
