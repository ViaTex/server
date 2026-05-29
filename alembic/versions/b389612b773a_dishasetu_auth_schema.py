"""DishaSetu Auth Schema

Revision ID: b389612b773a
Revises: 
Create Date: 2026-02-27 07:34:19.030684

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'b389612b773a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(conn, table_name: str) -> bool:
    return inspect(conn).has_table(table_name)

def index_exists(conn, table_name: str, index_name: str) -> bool:
    indexes = inspect(conn).get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)

def enum_exists(conn, enum_name: str) -> bool:
    return conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :name)"),
        {"name": enum_name}
    ).scalar()


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------ #
    # 1. Enums
    # ------------------------------------------------------------------ #
    if not enum_exists(conn, 'userstatus'):
        op.execute("CREATE TYPE userstatus AS ENUM ('ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING');")

    if not enum_exists(conn, 'gender'):
        op.execute("CREATE TYPE gender AS ENUM ('MALE', 'FEMALE', 'OTHER');")

    if not enum_exists(conn, 'usertype'):
        op.execute("CREATE TYPE usertype AS ENUM ('STUDENT', 'CORPORATE', 'UNIVERSITY', 'ADMIN');")

    user_status = postgresql.ENUM('ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING', name='userstatus', create_type=False)
    gender      = postgresql.ENUM('MALE', 'FEMALE', 'OTHER', name='gender', create_type=False)
    user_type   = postgresql.ENUM('STUDENT', 'CORPORATE', 'UNIVERSITY', 'ADMIN', name='usertype', create_type=False)

    # ------------------------------------------------------------------ #
    # 2. Universities
    # ------------------------------------------------------------------ #
    if not table_exists(conn, 'universities'):
        op.create_table(
            'universities',
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
            sa.Column('university_name', sa.String(length=255), nullable=False),
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
        op.create_index(op.f('ix_universities_email'), 'universities', ['email'], unique=True)

    # ------------------------------------------------------------------ #
    # 3. Students
    # ------------------------------------------------------------------ #
    if not table_exists(conn, 'students'):
        op.create_table(
            'students',
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
            sa.Column('institution', sa.String(length=255), nullable=True),
            sa.Column('degree', sa.String(length=100), nullable=True),
            sa.Column('branch', sa.String(length=100), nullable=True),
            sa.Column('graduation_year', sa.Integer(), nullable=True),
            sa.Column('major', sa.String(length=100), nullable=True),
            sa.Column('dob', sa.Date(), nullable=True),
            sa.Column('gender', gender, nullable=True),
            sa.Column('country', sa.String(length=100), nullable=True),
            sa.Column('state', sa.String(length=100), nullable=True),
            sa.Column('city', sa.String(length=100), nullable=True),
            sa.Column('tenth_grade_percentage', sa.Float(), nullable=True),
            sa.Column('twelfth_grade_percentage', sa.Float(), nullable=True),
            sa.Column('btech_cgpa', sa.Float(), nullable=True),
            sa.Column('technical_skills', sa.Text(), nullable=True),
            sa.Column('soft_skills', sa.Text(), nullable=True),
            sa.Column('certifications', sa.Text(), nullable=True),
            sa.Column('preferred_industry', sa.String(length=255), nullable=True),
            sa.Column('job_roles_of_interest', sa.String(length=255), nullable=True),
            sa.Column('location_preferences', sa.String(length=255), nullable=True),
            sa.Column('language_proficiency', sa.Text(), nullable=True),
            sa.Column('extracurricular_activities', sa.Text(), nullable=True),
            sa.Column('internship_experience', sa.Text(), nullable=True),
            sa.Column('project_details', sa.Text(), nullable=True),
            sa.Column('linkedin_profile', sa.String(length=500), nullable=True),
            sa.Column('github_profile', sa.String(length=500), nullable=True),
            sa.Column('personal_website', sa.String(length=500), nullable=True),
            sa.Column('college_id', sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_students_email'), 'students', ['email'], unique=True)

    # ------------------------------------------------------------------ #
    # 4. Corporates
    # ------------------------------------------------------------------ #
    if not table_exists(conn, 'corporates'):
        op.create_table(
            'corporates',
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
            sa.Column('company_name', sa.String(length=255), nullable=False),
            sa.Column('website_url', sa.String(length=500), nullable=True),
            sa.Column('industry', sa.String(length=255), nullable=True),
            sa.Column('company_size', sa.String(length=50), nullable=True),
            sa.Column('founded_year', sa.Integer(), nullable=True),
            sa.Column('contact_person', sa.String(length=255), nullable=True),
            sa.Column('contact_designation', sa.String(length=255), nullable=True),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('company_type', sa.String(length=100), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_corporates_email'), 'corporates', ['email'], unique=True)

    # ------------------------------------------------------------------ #
    # 5. Admins
    # ------------------------------------------------------------------ #
    if not table_exists(conn, 'admins'):
        op.create_table(
            'admins',
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
            sa.Column('role', sa.String(length=100), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_admins_email'), 'admins', ['email'], unique=True)

    # ------------------------------------------------------------------ #
    # 6. Email OTPs
    # ------------------------------------------------------------------ #
    if not table_exists(conn, 'email_otps'):
        op.create_table(
            'email_otps',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('code', sa.String(length=10), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('used', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_email_otps_email'), 'email_otps', ['email'], unique=False)

    # ------------------------------------------------------------------ #
    # 7. Password Reset OTPs
    # ------------------------------------------------------------------ #
    if not table_exists(conn, 'password_reset_otps'):
        op.create_table(
            'password_reset_otps',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('code', sa.String(length=6), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('used', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_password_reset_otps_email'), 'password_reset_otps', ['email'], unique=False)

    # ------------------------------------------------------------------ #
    # 8. User Sessions
    # ------------------------------------------------------------------ #
    if not table_exists(conn, 'user_sessions'):
        op.create_table(
            'user_sessions',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('user_type', user_type, nullable=False),
            sa.Column('session_token', sa.String(length=500), nullable=False),
            sa.Column('refresh_token', sa.String(length=500), nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.Text(), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('last_activity', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('session_token')
        )


def downgrade() -> None:
    conn = op.get_bind()

    if table_exists(conn, 'user_sessions'):
        op.drop_table('user_sessions')

    if table_exists(conn, 'password_reset_otps'):
        op.drop_index(op.f('ix_password_reset_otps_email'), table_name='password_reset_otps')
        op.drop_table('password_reset_otps')

    if table_exists(conn, 'email_otps'):
        op.drop_index(op.f('ix_email_otps_email'), table_name='email_otps')
        op.drop_table('email_otps')

    if table_exists(conn, 'admins'):
        op.drop_index(op.f('ix_admins_email'), table_name='admins')
        op.drop_table('admins')

    if table_exists(conn, 'corporates'):
        op.drop_index(op.f('ix_corporates_email'), table_name='corporates')
        op.drop_table('corporates')

    if table_exists(conn, 'students'):
        op.drop_index(op.f('ix_students_email'), table_name='students')
        op.drop_table('students')

    if table_exists(conn, 'universities'):
        op.drop_index(op.f('ix_universities_email'), table_name='universities')
        op.drop_table('universities')

    # Drop enums only if no other tables use them
    if not enum_exists(conn, 'userstatus'):
        op.execute("DROP TYPE IF EXISTS userstatus;")
    if not enum_exists(conn, 'gender'):
        op.execute("DROP TYPE IF EXISTS gender;")
    if not enum_exists(conn, 'usertype'):
        op.execute("DROP TYPE IF EXISTS usertype;")