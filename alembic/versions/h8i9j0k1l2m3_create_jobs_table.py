"""Create jobs table

Revision ID: h8i9j0k1l2m3
Revises: g2h3i4j5k6l7
Create Date: 2026-03-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "g2h3i4j5k6l7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


jobtype_enum = sa.Enum("full_time", "part_time", "contract", "internship", "freelance", name="jobtype")
jobstatus_enum = sa.Enum("active", "inactive", "closed", "draft", name="jobstatus")
jobtype_enum_existing = postgresql.ENUM(
    "full_time",
    "part_time",
    "contract",
    "internship",
    "freelance",
    name="jobtype",
    create_type=False,
)
jobstatus_enum_existing = postgresql.ENUM(
    "active",
    "inactive",
    "closed",
    "draft",
    name="jobstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    jobtype_enum.create(bind, checkfirst=True)
    jobstatus_enum.create(bind, checkfirst=True)

    if not inspector.has_table("jobs"):
        op.create_table(
            "jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("requirements", sa.Text(), nullable=True),
            sa.Column("responsibilities", sa.Text(), nullable=True),
            sa.Column("job_type", jobtype_enum_existing, nullable=False),
            sa.Column("status", jobstatus_enum_existing, nullable=True),
            sa.Column("location", sa.String(length=255), nullable=False),
            sa.Column("remote_work", sa.Boolean(), nullable=True),
            sa.Column("travel_required", sa.Boolean(), nullable=True),
            sa.Column("mode_of_work", sa.String(length=50), nullable=True),
            sa.Column("salary_min", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column("salary_max", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column("salary_currency", sa.String(length=3), nullable=True),
            sa.Column("ctc_with_probation", sa.String(length=255), nullable=True),
            sa.Column("ctc_after_probation", sa.String(length=255), nullable=True),
            sa.Column("experience_min", sa.Integer(), nullable=True),
            sa.Column("experience_max", sa.Integer(), nullable=True),
            sa.Column("education_level", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("education_degree", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("education_branch", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("skills_required", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("certifications_required", sa.Text(), nullable=True),
            sa.Column("application_deadline", sa.DateTime(timezone=True), nullable=True),
            sa.Column("max_applications", sa.Integer(), nullable=True),
            sa.Column("current_applications", sa.Integer(), nullable=True),
            sa.Column("number_of_openings", sa.Integer(), nullable=True),
            sa.Column("expiration_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("corporate_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("college_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("industry", sa.String(length=255), nullable=True),
            sa.Column("joining_location", sa.String(length=255), nullable=True),
            sa.Column("company_name", sa.String(length=255), nullable=True),
            sa.Column("company_logo", sa.Text(), nullable=True),
            sa.Column("company_website", sa.String(length=500), nullable=True),
            sa.Column("company_address", sa.String(length=500), nullable=True),
            sa.Column("company_size", sa.String(length=50), nullable=True),
            sa.Column("company_type", sa.String(length=100), nullable=True),
            sa.Column("company_founded", sa.Integer(), nullable=True),
            sa.Column("company_description", sa.Text(), nullable=True),
            sa.Column("contact_person", sa.String(length=255), nullable=True),
            sa.Column("contact_designation", sa.String(length=255), nullable=True),
            sa.Column("perks_and_benefits", sa.Text(), nullable=True),
            sa.Column("eligibility_criteria", sa.Text(), nullable=True),
            sa.Column("selection_process", sa.Text(), nullable=True),
            sa.Column("campus_drive_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("service_agreement_details", sa.Text(), nullable=True),
            sa.Column("min_des_score", sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column("max_des_score", sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column("ongoing_project_title", sa.String(length=255), nullable=True),
            sa.Column("ongoing_project_description", sa.Text(), nullable=True),
            sa.Column("views_count", sa.Integer(), nullable=True),
            sa.Column("applications_count", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("tenant_id", sa.String(length=50), nullable=False),
            sa.Column("is_public", sa.Boolean(), nullable=True),
            sa.Column("public_link_token", sa.String(length=255), nullable=True),
            sa.ForeignKeyConstraint(["college_id"], ["colleges.id"]),
            sa.ForeignKeyConstraint(["corporate_id"], ["corporates.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("public_link_token"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("jobs"):
        op.drop_table("jobs")

    jobstatus_enum.drop(bind, checkfirst=True)
    jobtype_enum.drop(bind, checkfirst=True)
