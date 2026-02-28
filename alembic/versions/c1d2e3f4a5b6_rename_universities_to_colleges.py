"""Rename universities table to colleges and update usertype enum

Revision ID: c1d2e3f4a5b6
Revises: b389612b773a
Create Date: 2026-02-27 10:38:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'b389612b773a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Rename the universities table to colleges
    # Check if the table exists before renaming
    table_exists = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'universities')"
    )).scalar()

    if table_exists:
        op.rename_table('universities', 'colleges')
        # Rename university_name column to college_name
        op.alter_column('colleges', 'university_name', new_column_name='college_name')
        # Rename the index
        op.drop_index('ix_universities_email', table_name='colleges')
        op.create_index('ix_colleges_email', 'colleges', ['email'], unique=True)
    else:
        # If universities table doesn't exist, create colleges table fresh
        user_status = postgresql.ENUM('ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING', name='userstatus', create_type=False)
        op.create_table('colleges',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('password_hash', sa.String(length=255), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('phone', sa.String(length=20), nullable=True),
            sa.Column('status', user_status, nullable=True),
            sa.Column('email_verified', sa.Boolean(), nullable=True),
            sa.Column('phone_verified', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
            sa.Column('college_name', sa.String(length=255), nullable=True),
            sa.Column('website_url', sa.String(length=500), nullable=True),
            sa.Column('institute_type', sa.String(length=100), nullable=True),
            sa.Column('established_year', sa.Integer(), nullable=True),
            sa.Column('contact_person_name', sa.String(length=255), nullable=True),
            sa.Column('contact_designation', sa.String(length=255), nullable=True),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('courses_offered', sa.Text(), nullable=True),
            sa.Column('branch', sa.String(length=255), nullable=True),
            sa.Column('college_id', sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_colleges_email', 'colleges', ['email'], unique=True)

    # 2. Update the usertype enum to replace UNIVERSITY with COLLEGE
    # PostgreSQL requires recreating the enum to rename a value
    # First check if COLLEGE already exists in the enum
    has_college = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'COLLEGE' AND enumtypid = 'usertype'::regtype)"
    )).scalar()
    has_university = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'UNIVERSITY' AND enumtypid = 'usertype'::regtype)"
    )).scalar()

    if has_university and not has_college:
        # Rename the UNIVERSITY value to COLLEGE in the enum
        conn.execute(sa.text("ALTER TYPE usertype RENAME VALUE 'UNIVERSITY' TO 'COLLEGE'"))


def downgrade() -> None:
    conn = op.get_bind()

    # Rename COLLEGE back to UNIVERSITY in enum
    has_college = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = 'COLLEGE' AND enumtypid = 'usertype'::regtype)"
    )).scalar()
    if has_college:
        conn.execute(sa.text("ALTER TYPE usertype RENAME VALUE 'COLLEGE' TO 'UNIVERSITY'"))

    # Rename colleges table back to universities
    table_exists = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'colleges')"
    )).scalar()
    if table_exists:
        op.drop_index('ix_colleges_email', table_name='colleges')
        op.alter_column('colleges', 'college_name', new_column_name='university_name')
        op.rename_table('colleges', 'universities')
        op.create_index('ix_universities_email', 'universities', ['email'], unique=True)
